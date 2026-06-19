import math
import time
from collections import deque
from statistics import median

import cv2 as cv


class SideProcessor:
    def __init__(self):
        self.rep_count = 0
        self.stage = "idle"

        self.leg_correct = True
        self.body_correct = True

        # Tresholdy błędów
        self.LEG_MIN_ANGLE = 155
        self.BODY_MIN_ANGLE = 75
        self.BODY_MAX_ANGLE = 115
        self.MAX_HIP_WRIST_RATIO = 1.15

        # System anti-flicker (Debouncing Faz)
        self.PHASE_COOLDOWN_FRAMES = 30
        self.frames_since_stage_change = 0

        self.LANDMARK_HISTORY = 4
        self.ERROR_TRIGGER_TIME = 0.3
        self.ERROR_DISPLAY_TIME = 3.0

        self.IDLE_TO_ACTIVE_FRAMES = 10
        self.ACTIVE_TO_IDLE_FRAMES = 20
        self.active_vote_counter = 0
        self.idle_vote_counter = 0

        self.history = [deque(maxlen=self.LANDMARK_HISTORY) for _ in range(33)]
        self.ratio_history = deque(maxlen=5)

        self.error_start_time = {}
        self.error_active_until = {}

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

    def _calculate_vectors_angle(self, v1_x, v1_y, v2_x, v2_y):
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

        self.frames_since_stage_change += 1

        # Wybór lepiej widocznej strony
        raw_r_shoulder = raw_landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        raw_l_shoulder = raw_landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
        raw_r_hip = raw_landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
        raw_l_hip = raw_landmarks[mp_pose.PoseLandmark.LEFT_HIP]

        r_visibility = raw_r_shoulder.visibility + raw_r_hip.visibility
        l_visibility = raw_l_shoulder.visibility + raw_l_hip.visibility

        is_right_side_active = r_visibility > l_visibility

        if is_right_side_active:
            shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
            elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
            wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
            hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
            knee = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE]
            ankle = landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE]
            ear = landmarks[mp_pose.PoseLandmark.RIGHT_EAR]
            raw_ear = raw_landmarks[mp_pose.PoseLandmark.RIGHT_EAR]
        else:
            shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
            elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]
            wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
            hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
            knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE]
            ankle = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE]
            ear = landmarks[mp_pose.PoseLandmark.LEFT_EAR]
            raw_ear = raw_landmarks[mp_pose.PoseLandmark.LEFT_EAR]

        # Wymagane punkty z obu stron dla kątów nóg
        r_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
        r_knee = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE]
        r_ankle = landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE]

        l_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
        l_knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE]
        l_ankle = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE]

        # --- OBLICZENIA GEOMETRYCZNE ---
        trunk_length = self._distance(shoulder, hip)
        if trunk_length == 0:
            trunk_length = 1.0

        elbow_angle = self._calculate_angle(shoulder, elbow, wrist)
        body_angle = self._calculate_angle(shoulder, hip, knee)
        arm_trunk_angle = self._calculate_angle(elbow, shoulder, hip)

        right_knee_angle = self._calculate_angle(r_hip, r_knee, r_ankle)
        left_knee_angle = self._calculate_angle(l_hip, l_knee, l_ankle)

        leg_angle = self._calculate_angle(hip, knee, ankle)
        leg_ground_angle = abs(
            math.degrees(math.atan2(hip["y"] - ankle["y"], hip["x"] - ankle["x"]))
        )

        v_r_leg_x = r_ankle["x"] - r_hip["x"]
        v_r_leg_y = r_ankle["y"] - r_hip["y"]
        v_l_leg_x = l_ankle["x"] - l_hip["x"]
        v_l_leg_y = l_ankle["y"] - l_hip["y"]
        legs_parallel_angle = self._calculate_vectors_angle(
            v_r_leg_x, v_r_leg_y, v_l_leg_x, v_l_leg_y
        )

        hip_wrist_dist = abs(hip["x"] - wrist["x"])
        shoulder_elbow_dist = self._distance(shoulder, elbow)

        if shoulder_elbow_dist > 0:
            self.ratio_history.append(hip_wrist_dist / shoulder_elbow_dist)
        else:
            self.ratio_history.append(0)
        hip_wrist_ratio = sum(self.ratio_history) / len(self.ratio_history)

        # --- GŁOSOWANIE NA STAN ĆWICZENIA (IDLE / ACTIVE) ---
        mandatory_legs_parallel = legs_parallel_angle < 35.0
        mandatory_body_angle = 70 < body_angle < 160
        mandatory_knees_straight = (right_knee_angle >= 150) and (
            left_knee_angle >= 150
        )

        optional_votes = 0
        if (wrist["x"] - hip["x"]) * (ankle["x"] - hip["x"]) < 0:
            optional_votes += 1
        if leg_ground_angle < 65:
            optional_votes += 1
        if raw_ear.visibility > 0.4:
            if (ear["x"] - hip["x"]) * (ankle["x"] - hip["x"]) > -0.1 * trunk_length:
                optional_votes += 1

        IS_DIP_POSE = (
            mandatory_legs_parallel
            and mandatory_body_angle
            and mandatory_knees_straight
            and (optional_votes >= 1)
        )

        if self.stage == "idle":
            if IS_DIP_POSE:
                self.active_vote_counter += 1
                self.idle_vote_counter = 0
            else:
                self.active_vote_counter = 0

            if self.active_vote_counter >= self.IDLE_TO_ACTIVE_FRAMES:
                self.stage = "down"  # Startujemy od opuszczania się
                self.active_vote_counter = 0
                self.exercise_started = True
                self.frames_since_stage_change = 0
        else:
            if not IS_DIP_POSE:
                self.idle_vote_counter += 1
                self.active_vote_counter = 0
            else:
                self.idle_vote_counter = 0

            if self.idle_vote_counter >= self.ACTIVE_TO_IDLE_FRAMES:
                if self.stage == "up":
                    self.rep_count += 1
                self.stage = "idle"
                self.idle_vote_counter = 0
                self.exercise_started = False

        # --- GŁOSOWANIE NA FAZY (UP / DOWN) ---
        top_votes = 0  # Głosy za byciem na GÓRZE (w pozycji wyjściowej)
        bottom_votes = 0  # Głosy za byciem na DOLE (w największym ugięciu)

        if (
            self.stage != "idle"
            and self.frames_since_stage_change > self.PHASE_COOLDOWN_FRAMES
        ):

            # WARUNKI BYCIA W POZYCJI NAJWYŻSZEJ (TOP)
            if elbow_angle > 140:
                top_votes += 1
            if arm_trunk_angle < 50:
                top_votes += 1
            if abs(hip["y"] - wrist["y"]) < trunk_length * 0.4:
                top_votes += 1
            if shoulder["y"] < elbow["y"] - trunk_length * 0.15:
                top_votes += 1

            # WARUNKI BYCIA W POZYCJI NAJNIŻSZEJ (BOTTOM)
            if elbow_angle < 120:
                bottom_votes += 1
            if arm_trunk_angle > 70:
                bottom_votes += 1
            if hip["y"] > wrist["y"] + trunk_length * 0.1:
                bottom_votes += 1
            if abs(shoulder["y"] - elbow["y"]) < trunk_length * 0.3:
                bottom_votes += 1

            # PRAWIDŁOWE PRZEŁĄCZANIE FAZ

            if self.stage == "down":
                # Jesteśmy w trakcie OPUSZCZANIA (down). Czekamy, aż osiągniemy dół.
                if bottom_votes >= 3:
                    self.stage = (
                        "up"  # Osiągnęliśmy dół, więc teraz zaczynamy WYPYCHANIE (up)
                    )
                    self.frames_since_stage_change = 0

            elif self.stage == "up":
                # Jesteśmy w trakcie WYPYCHANIA (up). Czekamy, aż osiągniemy górę.
                if top_votes >= 3:
                    self.rep_count += 1
                    self.stage = "down"  # Osiągnęliśmy górę, powtórzenie zaliczone, zaczynamy OPUSZCZANIE (down)
                    self.frames_since_stage_change = 0

        # --- SYSTEM BŁĘDÓW WIZUALNYCH ---
        active_messages = set()
        all_tests_passed = True
        self.leg_correct = True
        self.body_correct = True

        if self.stage != "idle":
            if leg_angle <= self.LEG_MIN_ANGLE:
                active_messages.add("Legs should be more straight")
                self.leg_correct = False
                all_tests_passed = False

            if self.stage == "down" and not (
                self.BODY_MIN_ANGLE <= body_angle <= self.BODY_MAX_ANGLE
            ):
                active_messages.add("Keep ~90 deg torso angle")
                self.body_correct = False
                all_tests_passed = False

            if self.stage == "up" and hip_wrist_ratio > self.MAX_HIP_WRIST_RATIO:
                active_messages.add("Body should be closer to bench")
                all_tests_passed = False

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

        # Debug Pasek (Zmienione nazwy głosów dla jasności)
        cv.putText(
            frame,
            f"Top_V:{top_votes}/4 Btm_V:{bottom_votes}/4 Cooldown:{self.frames_since_stage_change}",
            (15, h - 20),
            cv.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )

        return frame
