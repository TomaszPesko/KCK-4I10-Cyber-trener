import cv2 as cv
import math
import mediapipe as mp


class FrontProcessor:
    def __init__(self):
        # Repetition variables
        self.rep_count = 0
        self.stage = "up"

        # Thresholds
        self.DOWN_THRESHOLD = 0.04
        self.UP_THRESHOLD = 0.10
        self.HAND_MIN = 0.18
        self.HAND_MAX = 0.42

        # Feedback dla zewnętrznego systemu
        self.hand_feedback = "OK"

    def _distance(self, a, b):
        return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)

    def process(self, frame, landmarks, mp_pose, mp_draw):
        """Przetwarza klatkę, modyfikuje stan wewnętrzny i rysuje po klatce."""
        # Pobranie odpowiednich punktów (z zachowaniem Twojej logiki)
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        right_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
        right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
        left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]

        # Main height parameter
        shoulder_elbow_diff = abs(right_shoulder.y - right_elbow.y)

        # Wrist should stay below elbow
        proper_arm = right_wrist.y > right_elbow.y

        # Hand distance validation
        hand_distance = self._distance(left_wrist, right_wrist)
        hands_ok = self.HAND_MIN <= hand_distance <= self.HAND_MAX

        # Draw skeleton
        # Uwaga: rysujemy bezpośrednio na przekazanej klatce (będzie widoczna w get_agr_frame)
        # result_pose_landmarks musimy przekazać jako obiekt z MediaPipe (zrobimy to w głównym analyzerze)

        # Repetition logic
        if hands_ok and proper_arm:
            # Bottom position
            if shoulder_elbow_diff < self.DOWN_THRESHOLD:
                self.stage = "down"
            # Return to top
            elif shoulder_elbow_diff > self.UP_THRESHOLD and self.stage == "down":
                self.rep_count += 1
                self.stage = "up"

        # Hand placement feedback
        if hand_distance < self.HAND_MIN:
            self.hand_feedback = "Too narrow"
        elif hand_distance > self.HAND_MAX:
            self.hand_feedback = "Too wide"
        else:
            self.hand_feedback = "OK"

        # --- PANEL REZULTATÓW (OpenCV) ---
        cv.rectangle(frame, (0, 0), (520, 220), (0, 0, 0), -1)

        cv.putText(
            frame,
            f"Reps: {self.rep_count}",
            (20, 40),
            cv.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )
        cv.putText(
            frame,
            f"Stage: {self.stage}",
            (20, 80),
            cv.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2,
        )
        cv.putText(
            frame,
            f"Shoulder-Elbow diff: {shoulder_elbow_diff:.3f}",
            (20, 120),
            cv.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )
        cv.putText(
            frame,
            f"Hand distance: {hand_distance:.3f}",
            (20, 160),
            cv.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )

        feedback_color = (0, 255, 0) if self.hand_feedback == "OK" else (0, 0, 255)
        cv.putText(
            frame,
            f"Hands: {self.hand_feedback}",
            (20, 200),
            cv.FONT_HERSHEY_SIMPLEX,
            0.9,
            feedback_color,
            2,
        )

        return frame
