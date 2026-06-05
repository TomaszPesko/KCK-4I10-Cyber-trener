import cv2 as cv
import mediapipe as mp
import math

# MediaPipe setup
mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils

# Video
video = cv.VideoCapture("benchdipfrontdemo.mp4")

# Pose detector
pose = mp_pose.Pose(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)


def distance(a, b):
    return math.sqrt(
        (a.x - b.x) ** 2 +
        (a.y - b.y) ** 2
    )

# Repetition variables
rep_count = 0
stage = "up"

# -----------------------------
# Thresholds

# Shoulder-elbow vertical difference
DOWN_THRESHOLD = 0.04
UP_THRESHOLD = 0.10

# Hand separation validation
HAND_MIN = 0.18
HAND_MAX = 0.42

while video.isOpened():

    ok, frame = video.read()

    if not ok:
        break

    rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)

    result = pose.process(rgb)

    if result.pose_landmarks:

        landmarks = result.pose_landmarks.landmark

        # Right arm
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        right_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
        right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]

        # Left wrist
        left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]

        # -----------------------------
        # Main height parameter
        shoulder_elbow_diff = abs(
            right_shoulder.y - right_elbow.y
        )

        # Wrist should stay below elbow
        proper_arm = right_wrist.y > right_elbow.y


        # Hand distance validation
        hand_distance = distance(
            left_wrist,
            right_wrist
        )

        hands_ok = (
            HAND_MIN <= hand_distance <= HAND_MAX
        )

        # Draw skeleton
        mp_draw.draw_landmarks(
            frame,
            result.pose_landmarks,
            mp_pose.POSE_CONNECTIONS
        )

        # -----------------------------
        # Repetition logic
        # Only count if hand position valid

        if hands_ok and proper_arm:

            # Bottom position
            if shoulder_elbow_diff < DOWN_THRESHOLD:
                stage = "down"

            # Return to top
            elif (
                shoulder_elbow_diff > UP_THRESHOLD
                and stage == "down"
            ):
                rep_count += 1
                stage = "up"


        # Hand placement feedback
        hand_feedback = "OK"

        if hand_distance < HAND_MIN:
            hand_feedback = "Too narrow"

        elif hand_distance > HAND_MAX:
            hand_feedback = "Too wide"

        # Display panel
        cv.rectangle(
            frame,
            (0, 0),
            (520, 220),
            (0, 0, 0),
            -1
        )

        cv.putText(
            frame,
            f"Reps: {rep_count}",
            (20, 40),
            cv.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )

        cv.putText(
            frame,
            f"Stage: {stage}",
            (20, 80),
            cv.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2
        )

        cv.putText(
            frame,
            f"Shoulder-Elbow diff: {shoulder_elbow_diff:.3f}",
            (20, 120),
            cv.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

        cv.putText(
            frame,
            f"Hand distance: {hand_distance:.3f}",
            (20, 160),
            cv.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

        # Feedback color
        feedback_color = (0, 255, 0)

        if hand_feedback != "OK":
            feedback_color = (0, 0, 255)

        cv.putText(
            frame,
            f"Hands: {hand_feedback}",
            (20, 200),
            cv.FONT_HERSHEY_SIMPLEX,
            0.9,
            feedback_color,
            2
        )

    cv.imshow("Front Bench Dips Counter", frame)

    if cv.waitKey(1) & 0xFF == 27:
        break

video.release()
cv.destroyAllWindows()