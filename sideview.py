import cv2 as cv
import mediapipe as mp
import math
import time
from collections import deque
from statistics import median

mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils
ratio_history = deque(maxlen=5)

# Pose detector
pose = mp_pose.Pose(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Load video
video = cv.VideoCapture("benchdipsdemo.mp4")

# Fixed output resolution
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
LANDMARK_HISTORY = 4 # From how many frames the landmarks are smoothed
START_REQUIRED_FRAMES = 15
#-----------------------------
# Error system variables
ERROR_TRIGGER_TIME = 0.3
ERROR_DISPLAY_TIME = 3.0

# -----------------------------
# Form validation thresholds

# Elbow angle thresholds
BOTTOM_THRESHOLD = 120 # lower = stricter
TOP_THRESHOLD = 145 # higher = stricker

# Legs should stay almost straight
LEG_MIN_ANGLE = 155 # higher = stricker

# Torso angle near 90° at bottom, Closer to 90 = stricter
BODY_MIN_ANGLE = 75
BODY_MAX_ANGLE = 115

MAX_HIP_WRIST_RATIO = 1.15 # lower = stricter, carefull with this

ORIENTATION_LOST_TIME = 0.75 # Left the training position timer

# -----------------------------
# Calculation funtions

def distance(a, b):
    dx = a["x"] - b["x"]
    dy = a["y"] - b["y"]
    return math.sqrt(dx*dx + dy*dy)

def calculate_angle(a, b, c):

    ax, ay = a["x"], a["y"]
    bx, by = b["x"], b["y"]
    cx, cy = c["x"], c["y"]

    angle = math.degrees(
        math.atan2(cy - by, cx - bx) -
        math.atan2(ay - by, ax - bx)
    )

    angle = abs(angle)

    if angle > 180:
        angle = 360 - angle

    return angle


# -----------------------------
# Landmark smoothing

history = [
    deque(maxlen=LANDMARK_HISTORY)
    for _ in range(33)
]

def get_smoothed_landmarks(raw_landmarks):

    for idx, lm in enumerate(raw_landmarks):

        history[idx].append({
            "x": lm.x,
            "y": lm.y
        })

    if any(len(points) < LANDMARK_HISTORY for points in history):
        return None

    smoothed = []

    for points in history:
        smoothed.append({
            "x": median([p["x"] for p in points]),
            "y": median([p["y"] for p in points])
        })

    return smoothed


# -----------------------------
# ERROR SYSTEM

error_start_time = {}
error_active_until = {}


def register_error(message):

    now = time.time()

    if message not in error_start_time:
        error_start_time[message] = now

    if (
        now - error_start_time[message] >= ERROR_TRIGGER_TIME
        and message not in error_active_until
    ):
        error_active_until[message] = now + ERROR_DISPLAY_TIME


def clear_error(message):

    # reset continuous detection timer
    error_start_time.pop(message, None)

def is_confirmed_error(message):

    if message not in error_start_time:
        return False

    return (
        time.time() - error_start_time[message]
        >= ERROR_TRIGGER_TIME
    )

# -----------------------------
# Validation tests

def test_legs(data):

    message = "Legs should be more straight"

    if data["stage"] == "idle":
        return True, message

    if data["leg_angle"] <= LEG_MIN_ANGLE:
        return False, message

    return True, message


def test_body(data):

    message = "There should be ~90 deg. angle between torso and legs"

    if data["stage"] == "idle":
        return True, message

    if (
        data["stage"] == "down"
        and not (BODY_MIN_ANGLE <= data["body_angle"] <= BODY_MAX_ANGLE)
    ):
        return False, message

    return True, message

def test_bench_distance(data):

    message = "Body should be closer to bench"

    if data["stage"] == "idle":
        return True, message

    if data["stage"] != "up":
        return True, message

    if data["hip_wrist_ratio"] > MAX_HIP_WRIST_RATIO:
        return False, message

    return True, message

tests = [
    test_legs,
    test_body,
    test_bench_distance
]

# -----------------------------
# Rep counter

rep_count = 0
stage = "idle"

correct_frames = 0
total_frames = 0
exercise_started = False

orientation_lost_start = None
start_counter = 0

# -----------------------------
# MAIN LOOP

while video.isOpened():

    ok, frame = video.read()
    if not ok:
        break

    frame = cv.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

    rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
    result = pose.process(rgb)
    if result.pose_landmarks is None:
        ratio_history.clear()
        if stage != "idle":
            stage = "idle"
            start_counter = 0
            exercise_started = False

        cv.imshow("Bench Dips Counter", frame)

        if cv.waitKey(1) & 0xFF == 27:
            break

        continue

    if result.pose_landmarks:

        raw_landmarks = result.pose_landmarks.landmark
        landmarks = get_smoothed_landmarks(raw_landmarks)

        if landmarks is None:
            continue

        shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
        wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]

        hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
        knee = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE]
        ankle = landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE]

        elbow_angle = calculate_angle(shoulder, elbow, wrist)
        leg_angle = calculate_angle(hip, knee, ankle)
        body_angle = calculate_angle(shoulder, hip, knee)


        hip_wrist_distance = abs(hip["x"] - wrist["x"])
        shoulder_elbow_distance = distance(shoulder, elbow)

        if shoulder_elbow_distance > 0:
            hip_wrist_ratio_raw = hip_wrist_distance / shoulder_elbow_distance
        else:
            hip_wrist_ratio_raw = 0

        ratio_history.append(hip_wrist_ratio_raw)
        hip_wrist_ratio = sum(ratio_history) / len(ratio_history) if ratio_history else 0

        wrist_x = wrist["x"]
        hip_x = hip["x"]
        knee_x = knee["x"]

        right_facing = wrist_x < hip_x < knee_x
        left_facing = knee_x < hip_x < wrist_x

        bench_dip_orientation = (right_facing or left_facing)

        if bench_dip_orientation:

            orientation_lost_start = None

        else:

            if orientation_lost_start is None:
                orientation_lost_start = time.time()

            elif (
                    time.time() - orientation_lost_start
                    >= ORIENTATION_LOST_TIME
            ):
                stage = "idle"
                start_counter = 0
                exercise_started = False

        START_POSITION = (
                elbow_angle > TOP_THRESHOLD
                and leg_angle > LEG_MIN_ANGLE
                and bench_dip_orientation
        )


        # -----------------------------
        # REP COUNT

        if stage == "idle":

            if START_POSITION:
                start_counter += 1
            else:
                start_counter = 0

            if start_counter >= START_REQUIRED_FRAMES:
                stage = "up"
                start_counter = 0

        elif stage == "up":

            if elbow_angle < BOTTOM_THRESHOLD:
                stage = "down"
                exercise_started = True

        elif stage == "down":

            if elbow_angle > TOP_THRESHOLD:
                rep_count += 1
                stage = "up"


        # -----------------------------
        # VALIDATION

        test_data = {
            "elbow_angle": elbow_angle,
            "leg_angle": leg_angle,
            "body_angle": body_angle,
            "hip_wrist_ratio": hip_wrist_ratio,
            "stage": stage
        }

        all_tests_passed = True
        active_messages = set()

        for test in tests:

            passed, message = test(test_data)

            if not passed:
                all_tests_passed = False
                register_error(message)
                active_messages.add(message)
            else:
                clear_error(message)

        # reset timers only for errors that disappeared
        for msg in list(error_start_time.keys()):
            if msg not in active_messages:
                error_start_time.pop(msg, None)

        confirmed_error = False

        for message in active_messages:

            if is_confirmed_error(message):
                confirmed_error = True
                break

        connection_color = (
            (0, 0, 255)
            if confirmed_error
            else
            (255, 255, 255)
        )

        mp_draw.draw_landmarks(
            frame,
            result.pose_landmarks,
            mp_pose.POSE_CONNECTIONS,
            connection_drawing_spec=mp_draw.DrawingSpec(
                color=connection_color,
                thickness=2
            )
        )

        # -----------------------------
        # FORM ACCURACY

        if exercise_started:
            total_frames += 1
            if all_tests_passed:
                correct_frames += 1

        accuracy = (
            correct_frames / total_frames * 100
        ) if total_frames > 0 else 0.0

        # -----------------------------
        # UI PANEL

        cv.rectangle(frame, (0, 0), (320, 130), (0, 0, 0), -1)

        cv.putText(
            frame,
            f"Reps: {rep_count}",
            (15, 35),
            cv.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            2
        )

        cv.putText(
            frame,
            f"Stage: {stage}",
            (15, 75),
            cv.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2
        )

        cv.putText(
            frame,
            f"Form: {accuracy:.1f}%",
            (15, 115),
            cv.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 0),
            2
        )

        # -----------------------------
        # WARNINGS (FIXED DISPLAY)

        now = time.time()
        warning_y = 170

        expired = []

        for message, end_time in error_active_until.items():

            if now <= end_time:

                cv.putText(
                    frame,
                    message,
                    (15, warning_y),
                    cv.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2
                )

                warning_y += 40

            else:
                expired.append(message)

        # remove only expired warnings
        for msg in expired:
            error_active_until.pop(msg, None)

        # -----------------------------
        # DEBUG

        cv.putText(
            frame,
            f"ElbowA:{int(elbow_angle)} LegsA:{int(leg_angle)} BodyA:{int(body_angle)} BenchDistance:{hip_wrist_ratio:.2f}",
            (15, frame.shape[0] - 20),
            cv.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1
        )

    cv.imshow("Bench Dips Counter", frame)

    if cv.waitKey(1) & 0xFF == 27:
        break

video.release()
cv.destroyAllWindows()