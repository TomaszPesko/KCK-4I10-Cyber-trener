import math
import time
from collections import deque
from statistics import median

import cv2 as cv


class FrontProcessor:
    def __init__(self):
        # Zmienne powtórzeń i stanów
        self.rep_count = 0
        self.stage = "idle"  # idle -> down -> up -> (rep++) down...
        self.hand_feedback = "OK"

        # --- Zaktualizowane progi na bazie analizy wideo ---
        # Zwiększony wskaźnik: łokieć może być niżej niż linia barków (ok 25% długości tułowia poniżej)
        self.BOTTOM_ELBOW_SHOULDER_RATIO = 0.25
        # Zwiększony kąt: nie wymagamy pełnego "przeprostu" łokcia na górze
        self.TOP_ARM_TRUNK_ANGLE = 50.0

        self.HAND_MIN = 1.0
        self.HAND_MAX = 4.0

        # --- System anti-flicker (Debouncing Faz) ---
        # Zablokowanie mrugania: zmiana fazy (up <-> down) możliwa dopiero po upływie 30 klatek (~1 sekunda)
        self.PHASE_COOLDOWN_FRAMES = 30
        self.frames_since_stage_change = 0

        self.LANDMARK_HISTORY = 4
        self.ERROR_TRIGGER_TIME = 0.3
        self.ERROR_DISPLAY_TIME = 3.0

        self.IDLE_TO_ACTIVE_FRAMES = 10
        self.ACTIVE_TO_IDLE_FRAMES = 20
        self.active_vote_counter = 0
        self.idle_vote_counter = 0

        # Historia do wygładzania punktów (Median Filter)
        self.history = [deque(maxlen=self.LANDMARK_HISTORY) for _ in range(33)]

        self.error_start_time = {}
        self.error_active_until = {}

        # Zmienne kontrolne
        self.exercise_started = False
        self.correct_frames = 0
        self.total_frames = 0

    def _distance(self, a, b):
        return math.sqrt((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2)

    def _calculate_angle(self, a, b, c):
        angle = math.degrees(
            math.atan2(c["y"] - b["y"], c["x"] - b["x"])
            - math.atan2(a["y"] - b["y"], a["x"] - b["x"])
        )
        angle = abs(angle)
        return 360 - angle if angle > 180 else angle

    def _calculate_vectors_angle(self, p_center, p1, p2):
        """Oblicza kąt między dwoma wektorami wychodzącymi z jednego punktu."""
        v1_x = p1["x"] - p_center["x"]
        v1_y = p1["y"] - p_center["y"]
        v2_x = p2["x"] - p_center["x"]
        v2_y = p2["y"] - p_center["y"]

        dot_product = v1_x * v2_x + v1_y * v2_y
        mag1 = math.sqrt(v1_x**2 + v1_y**2)
        mag2 = math.sqrt(v2_x**2 + v2_y**2)

        if mag1 * mag2 == 0:
            return 0

        cos_angle = max(-1.0, min(1.0, dot_product / (mag1 * mag2)))
        return math.degrees(math.acos(cos_angle))

    def _get_smoothed_landmarks(self, raw_landmarks, width, height):
        for idx, lm in enumerate(raw_landmarks):
            self.history[idx].append({"x": lm.x * width, "y": lm.y * height})

        if any(len(points) < self.LANDMARK_HISTORY for points in self.history):
            return None

        smoothed = []
        for points in self.history:
            smoothed.append(
                {
                    "x": median([p["x"] for p in points]),
                    "y": median([p["y"] for p in points]),
                }
            )
        return smoothed

    def _manage_errors(self, active_messages):
        now = time.time()
        for msg in active_messages:
            if msg not in self.error_start_time:
                self.error_start_time[msg] = now
            if now - self.error_start_time[msg] >= self.ERROR_TRIGGER_TIME:
                self.error_active_until[msg] = now + self.ERROR_DISPLAY_TIME

        for msg in list(self.error_start_time.keys()):
            if msg not in active_messages:
                self.error_start_time.pop(msg, None)

        expired = [
            msg for msg, end_time in self.error_active_until.items() if now > end_time
        ]
        for msg in expired:
            self.error_active_until.pop(msg, None)

    def process(self, frame, raw_landmarks, mp_pose, mp_draw):
        h, w = frame.shape[:2]
        landmarks = self._get_smoothed_landmarks(raw_landmarks, w, h)

        if landmarks is None:
            return frame

        # Zawsze zwiększamy licznik klatek od ostatniej zmiany
        self.frames_since_stage_change += 1

        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
        left_elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]
        right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
        left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
        right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
        left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
        right_knee = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE]
        left_knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE]
        right_ankle = landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE]
        left_ankle = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE]

        # Wybór lepiej widocznej strony (Okluzja)
        raw_r_elbow = raw_landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
        raw_l_elbow = raw_landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]

        if raw_r_elbow.visibility > raw_l_elbow.visibility:
            active_shoulder = right_shoulder
            active_elbow = right_elbow
            active_hip = right_hip
        else:
            active_shoulder = left_shoulder
            active_elbow = left_elbow
            active_hip = left_hip

        # OBLICZENIA GEOMETRYCZNE
        left_knee_angle = self._calculate_angle(left_hip, left_knee, left_ankle)
        right_knee_angle = self._calculate_angle(right_hip, right_knee, right_ankle)
        legs_straight = (left_knee_angle > 150) and (right_knee_angle > 150)

        proper_arm = (right_wrist["y"] > right_shoulder["y"]) and (
            left_wrist["y"] > left_shoulder["y"]
        )

        trunk_length = self._distance(active_shoulder, active_hip)
        if trunk_length == 0:
            trunk_length = 1.0

        elbow_shoulder_y_dist = max(0, active_elbow["y"] - active_shoulder["y"])
        elbow_height_ratio = elbow_shoulder_y_dist / trunk_length

        arm_trunk_angle = self._calculate_vectors_angle(
            active_shoulder, active_hip, active_elbow
        )

        hand_distance_raw = self._distance(left_wrist, right_wrist)
        hip_distance = self._distance(left_hip, right_hip)
        hand_ratio = (hand_distance_raw / hip_distance) if hip_distance > 0 else 0

        # --- MASZYNA STANÓW: WEJŚCIE I WYJŚCIE Z IDLE ---
        IS_DIP_POSE_DETECTED = legs_straight and proper_arm

        if self.stage == "idle":
            if IS_DIP_POSE_DETECTED:
                self.active_vote_counter += 1
                self.idle_vote_counter = 0
            else:
                self.active_vote_counter = 0

            if self.active_vote_counter >= self.IDLE_TO_ACTIVE_FRAMES:
                self.stage = "down"
                self.active_vote_counter = 0
                self.exercise_started = True
                self.frames_since_stage_change = (
                    0  # Resetujemy licznik opóźnienia przy wejściu
                )

        else:
            if not IS_DIP_POSE_DETECTED:
                self.idle_vote_counter += 1
                self.active_vote_counter = 0
            else:
                self.idle_vote_counter = 0

            if self.idle_vote_counter >= self.ACTIVE_TO_IDLE_FRAMES:
                self.stage = "idle"
                self.idle_vote_counter = 0
                self.exercise_started = False

        # --- MASZYNA STANÓW: FAZY ĆWICZENIA Z DEBOUNCINGIEM (OPÓŹNIENIEM) ---

        if self.stage == "down":
            # Możliwość zmiany fazy dopiero po 30 klatkach trwania fazy 'down'
            if (
                elbow_height_ratio < self.BOTTOM_ELBOW_SHOULDER_RATIO
                and self.frames_since_stage_change > self.PHASE_COOLDOWN_FRAMES
            ):
                self.stage = "up"
                self.frames_since_stage_change = 0  # Reset

        elif self.stage == "up":
            # Możliwość zmiany fazy dopiero po 30 klatkach trwania fazy 'up'
            if (
                arm_trunk_angle < self.TOP_ARM_TRUNK_ANGLE
                and self.frames_since_stage_change > self.PHASE_COOLDOWN_FRAMES
            ):
                self.rep_count += 1
                self.stage = "down"
                self.frames_since_stage_change = 0  # Reset

        # --- SYSTEM BŁĘDÓW WIZUALNYCH (AR) ---
        active_messages = set()
        all_tests_passed = True

        if self.stage != "idle":
            if hand_ratio < self.HAND_MIN:
                active_messages.add("Hands too narrow")
                self.hand_feedback = "Too narrow"
                all_tests_passed = False
            elif hand_ratio > self.HAND_MAX:
                active_messages.add("Hands too wide")
                self.hand_feedback = "Too wide"
                all_tests_passed = False
            else:
                self.hand_feedback = "OK"

            if not proper_arm:
                active_messages.add("Keep wrists below shoulders")
                all_tests_passed = False
        else:
            self.hand_feedback = "OK"

        self._manage_errors(active_messages)

        # --- STATYSTYKI ---
        if self.exercise_started and self.stage != "idle":
            self.total_frames += 1
            if all_tests_passed:
                self.correct_frames += 1
        accuracy = (
            (self.correct_frames / self.total_frames * 100)
            if self.total_frames > 0
            else 0.0
        )

        # --- WIDOK AR (OpenCV) ---
        cv.rectangle(frame, (0, 0), (320, 140), (0, 0, 0), -1)

        cv.putText(
            frame,
            f"Reps: {self.rep_count}",
            (15, 35),
            cv.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            2,
        )
        cv.putText(
            frame,
            f"Stage: {self.stage}",
            (15, 75),
            cv.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2,
        )
        cv.putText(
            frame,
            f"Form: {accuracy:.1f}%",
            (15, 115),
            cv.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 0),
            2,
        )

        warning_y = 170
        for message in self.error_active_until.keys():
            cv.putText(
                frame,
                message,
                (15, warning_y),
                cv.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2,
                cv.LINE_AA,
            )
            warning_y += 40

        # Ukryty pasek debugowy do kalibracji
        cv.putText(
            frame,
            f"Arm/Trunk Angle: {arm_trunk_angle:.1f} Elbow Height: {elbow_height_ratio:.2f}",
            (15, h - 20),
            cv.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1,
        )

        return frame
