import cv2 as cv
import math
import mediapipe as mp


class SideProcessor:
    def __init__(self):
        # Repetition variables
        self.rep_count = 0
        self.stage = "up"

        # Thresholds
        self.BOTTOM_THRESHOLD = 105
        self.TOP_THRESHOLD = 145
        self.LEG_MIN_ANGLE = 155
        self.BODY_MIN_ANGLE = 75
        self.BODY_MAX_ANGLE = 105

        # Stan walidacji sylwetki
        self.leg_correct = True
        self.body_correct = True

    def _calculate_angle(self, a, b, c):
        ax, ay = a.x, a.y
        bx, by = b.x, b.y
        cx, cy = c.x, c.y

        angle = math.degrees(
            math.atan2(cy - by, cx - bx) - math.atan2(ay - by, ax - bx)
        )
        angle = abs(angle)
        if angle > 180:
            angle = 360 - angle
        return angle

    def process(self, frame, landmarks, mp_pose, mp_draw):
        """Przetwarza klatkę boczna, sprawdza błędy, nanosi grafikę OpenCV."""
        # Upper body landmarks
        shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
        wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]

        # Lower body landmarks
        hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
        knee = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE]
        ankle = landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE]

        # Angle calculations
        elbow_angle = self._calculate_angle(shoulder, elbow, wrist)
        leg_angle = self._calculate_angle(hip, knee, ankle)
        body_angle = self._calculate_angle(shoulder, hip, knee)

        # Rep counting
        if elbow_angle < self.BOTTOM_THRESHOLD:
            self.stage = "down"
        elif elbow_angle > self.TOP_THRESHOLD and self.stage == "down":
            self.rep_count += 1
            self.stage = "up"

        # Form validation
        self.leg_correct = leg_angle > self.LEG_MIN_ANGLE
        self.body_correct = self.BODY_MIN_ANGLE <= body_angle <= self.BODY_MAX_ANGLE

        # --- PANEL INFORMACYJNY (OpenCV) ---
        cv.rectangle(frame, (0, 0), (260, 90), (0, 0, 0), -1)
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

        # Warning messages
        warning_y = 130
        if not self.leg_correct:
            cv.putText(
                frame,
                "Legs should be more straight",
                (15, warning_y),
                cv.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2,
            )
            warning_y += 40

        if not self.body_correct and self.stage == "down":
            cv.putText(
                frame,
                "There should be ~90 deg. angle between torso and legs",
                (15, warning_y),
                cv.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2,
            )

        # Debug info
        cv.putText(
            frame,
            f"E:{int(elbow_angle)}  L:{int(leg_angle)}  B:{int(body_angle)}",
            (15, frame.shape[0] - 20),
            cv.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1,
        )

        return frame
