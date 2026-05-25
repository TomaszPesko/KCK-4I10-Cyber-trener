import cv2 as cv
import mediapipe as mp
import math

mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils

# Load video
video = cv.VideoCapture("benchdipsdemo.mp4")

# Pose detector
pose = mp_pose.Pose(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

def calculate_angle(a, b, c):

    ax, ay = a.x, a.y
    bx, by = b.x, b.y
    cx, cy = c.x, c.y

    angle = math.degrees(
        math.atan2(cy - by, cx - bx) -
        math.atan2(ay - by, ax - bx)
    )

    angle = abs(angle)

    if angle > 180:
        angle = 360 - angle

    return angle


# Count rep when comes back to 'up'
rep_count = 0
stage = "up"

#---------------------------
# Form validation thresholds

# Elbow angle thresholds
BOTTOM_THRESHOLD = 105
TOP_THRESHOLD = 145

# Legs should stay almost straight
LEG_MIN_ANGLE = 155

# Torso angle near 90° at bottom
BODY_MIN_ANGLE = 75
BODY_MAX_ANGLE = 105


# -----------------------------
# Main loop
while video.isOpened():

    ok, frame = video.read()

    if not ok:
        break

    rgb = cv.cvtColor(
        frame,
        cv.COLOR_BGR2RGB
    )

    result = pose.process(rgb)

    if result.pose_landmarks:
        landmarks = result.pose_landmarks.landmark

        # Upper body landmarks

        shoulder = landmarks[
            mp_pose.PoseLandmark.RIGHT_SHOULDER
        ]

        elbow = landmarks[
            mp_pose.PoseLandmark.RIGHT_ELBOW
        ]

        wrist = landmarks[
            mp_pose.PoseLandmark.RIGHT_WRIST
        ]

        # Lower body landmarks

        hip = landmarks[
            mp_pose.PoseLandmark.RIGHT_HIP
        ]

        knee = landmarks[
            mp_pose.PoseLandmark.RIGHT_KNEE
        ]

        ankle = landmarks[
            mp_pose.PoseLandmark.RIGHT_ANKLE
        ]

        # Angle calculations
        #---------------------

        # Elbow angle
        elbow_angle = calculate_angle(
            shoulder,
            elbow,
            wrist
        )

        # Leg straightness
        leg_angle = calculate_angle(
            hip,
            knee,
            ankle
        )

        # Torso angle
        body_angle = calculate_angle(
            shoulder,
            hip,
            knee
        )

        # Draw skeleton
        mp_draw.draw_landmarks(
            frame,
            result.pose_landmarks,
            mp_pose.POSE_CONNECTIONS
        )

        #________________
        # Rep counting

        if elbow_angle < BOTTOM_THRESHOLD:
            stage = "down"

        elif (
            elbow_angle > TOP_THRESHOLD
            and stage == "down"
        ):
            rep_count += 1
            stage = "up"

        # -----------------------------
        # Form validation

        leg_correct = (
            leg_angle > LEG_MIN_ANGLE
        )

        body_correct = (
            BODY_MIN_ANGLE <= body_angle <= BODY_MAX_ANGLE
        )

        # -----------------------------
        # Info panel

        cv.rectangle(
            frame,
            (0, 0),
            (260, 90),
            (0, 0, 0),
            -1
        )

        # Reps
        cv.putText(
            frame,
            f"Reps: {rep_count}",
            (15, 35),
            cv.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            2
        )

        # Stage
        cv.putText(
            frame,
            f"Stage: {stage}",
            (15, 75),
            cv.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2
        )

        # -----------------------------
        # Warning messages

        warning_y = 130

        # Legs warning
        if not leg_correct:
            cv.putText(
                frame,
                "Legs should be more straight",
                (15, warning_y),
                cv.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2
            )
            warning_y += 40

        # Torso warning
        if (
            not body_correct
            and stage == "down"
        ):

            cv.putText(
                frame,
                "There should be ~90 deg. angle between torso and legs",
                (15, warning_y),
                cv.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2
            )

        # -----------------------------
        # Debug info

        cv.putText(
            frame,
            f"E:{int(elbow_angle)}  "
            f"L:{int(leg_angle)}  "
            f"B:{int(body_angle)}",
            (15, frame.shape[0] - 20),
            cv.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1
        )


    # Show frame
    cv.imshow(
        "Bench Dips Counter",
        frame
    )

    # ESC to exit
    if cv.waitKey(1) & 0xFF == 27:
        break

video.release()
cv.destroyAllWindows()