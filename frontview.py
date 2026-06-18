import cv2 as cv
import mediapipe as mp
import math
import time
from collections import deque

# MediaPipe setup
mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils

# Video
video = cv.VideoCapture("benchdipfrontdemo.mp4")

# Fixed output resolution
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

#Variables
ERROR_TRIGGER_TIME = 0.3
ERROR_DISPLAY_TIME = 3.0
LANDMARK_HISTORY = 4
START_REQUIRED_FRAMES = 15

# Thresholds

# Shoulder-elbow vertical difference
DOWN_THRESHOLD = 0.5
UP_THRESHOLD = 1.75

# Hand separation validation
HAND_MIN = 1
HAND_MAX = 4

# Pose detector
pose = mp_pose.Pose(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
hip_ratio_history = deque(maxlen=5)
prev_shoulder_elbow_diff = 0
prev_wrist_center = 0
prev_wrist_asymmetry = 0


def distance(a, b):

    return math.sqrt(
        (a["x"] - b["x"]) ** 2 +
        (a["y"] - b["y"]) ** 2
    )

stage = "idle"
exercise_started = False
orientation_lost_start = None
ORIENTATION_LOST_TIME = 0.75

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

    if any(
        len(points) < LANDMARK_HISTORY
        for points in history
    ):
        return None

    smoothed = []

    for points in history:

        smoothed.append({
            "x": sum(p["x"] for p in points) / len(points),
            "y": sum(p["y"] for p in points) / len(points)
        })

    return smoothed


# -----------------------------
# ERROR SYSTEM (FIXED)

error_first_seen = {}
active_errors = {}

def is_confirmed_error(message):
    return message in error_first_seen and (
        time.time() - error_first_seen[message] >= ERROR_TRIGGER_TIME
    )

def register_error(message):

    now = time.time()

    # zapamiętaj kiedy pierwszy raz zobaczono błąd
    if message not in error_first_seen:
        error_first_seen[message] = now

    # jeśli trwa wystarczająco długo → aktywuj
    if message not in active_errors:
        if now - error_first_seen[message] >= ERROR_TRIGGER_TIME:
            active_errors[message] = now + ERROR_DISPLAY_TIME


def clear_error(message):

    error_first_seen.pop(message, None)
    active_errors.pop(message, None)


# Repetition variables

rep_count = 0

start_counter = 0


# -----------------------------
# Form statistics

correct_frames = 0
total_frames = 0

# -----------------------------
# Validation tests

def test_hands(data):

    if data["hand_distance"] < HAND_MIN:
        return False, "Hands too narrow"

    if data["hand_distance"] > HAND_MAX:
        return False, "Hands too wide"

    return True, ""


def test_arm(data):

    if not data["proper_arm"]:
        return False, "Keep wrists below elbows"

    return True, ""


tests = [
    test_hands,
    test_arm
]


# -----------------------------
# Main loop

while video.isOpened():

    ok, frame = video.read()

    if not ok:
        break

    frame = cv.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

    rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)

    result = pose.process(rgb)

    if result.pose_landmarks is None:

        hip_ratio_history.clear()

        if stage != "idle":
            stage = "idle"
            start_counter = 0
            exercise_started = False

        cv.imshow("Front Bench Dips Counter", frame)

        if cv.waitKey(1) & 0xFF == 27:
            break

        continue

    confirmed_error = False
    connection_color = (255, 255, 255)
    active_messages = set()

    if result.pose_landmarks:

        raw_landmarks = result.pose_landmarks.landmark
        landmarks = get_smoothed_landmarks(raw_landmarks)

        if landmarks is None:
            continue

        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        right_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
        right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
        left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]

        wrist_center = (left_wrist["y"] + right_wrist["y"]) / 2
        wrist_asymmetry = abs(left_wrist["y"] - right_wrist["y"])

        left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
        right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]

        hip_asymmetry = abs(left_hip["y"] - right_hip["y"])

        proper_arm = (
            right_wrist["y"] > right_elbow["y"]
        )

        hand_distance_raw = distance(left_wrist, right_wrist)
        hip_distance = distance(left_hip, right_hip)

        if hip_distance > 0:
            hand_ratio_raw = hand_distance_raw / hip_distance
        else:
            hand_ratio_raw = 0

        hip_ratio_history.append(hand_ratio_raw)

        hand_distance = (
            sum(hip_ratio_history) / len(hip_ratio_history)
            if hip_ratio_history else 0
        )

        if hip_distance > 0:
            shoulder_elbow_diff = abs(right_shoulder["y"] - right_elbow["y"]) / hip_distance
        else:
            shoulder_elbow_diff = 0

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
        # VALIDATION

        test_data = {
            "hand_distance": hand_distance,
            "proper_arm": proper_arm
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

        for msg in list(error_first_seen.keys()):
            if msg not in active_messages:
                error_first_seen.pop(msg, None)
                active_errors.pop(msg, None)

        for message in active_messages:
            if is_confirmed_error(message):
                confirmed_error = True
                break

        connection_color = (
            (0, 0, 255) if confirmed_error else (255, 255, 255)
        )
        # -----------------------------
        # Repetition logic
        hip_asymmetry = abs(left_hip["y"] - right_hip["y"])

        wrist_motion = abs(wrist_center - prev_wrist_center)
        asymmetry_motion = abs(wrist_asymmetry - prev_wrist_asymmetry)

        stable_wrists = wrist_motion < 0.01
        stable_symmetry = asymmetry_motion < 0.01

        motion_free = stable_wrists and stable_symmetry

        stable_body = shoulder_elbow_diff > 0.15 and shoulder_elbow_diff < 1.2

        START_POSITION = (
                all_tests_passed
                and HAND_MIN < hand_distance < HAND_MAX
                and stable_body
                and motion_free
        )

        if stage == "idle":
            if START_POSITION:
                start_counter += 1
            else:
                start_counter = 0

            if start_counter >= START_REQUIRED_FRAMES:
                stage = "up"
                start_counter = 0


        elif stage == "up":

            if shoulder_elbow_diff < DOWN_THRESHOLD:
                stage = "down"
                exercise_started = True

        elif stage == "down":

            if shoulder_elbow_diff > UP_THRESHOLD:
                rep_count += 1
                stage = "up"

        prev_shoulder_elbow_diff = shoulder_elbow_diff
        prev_wrist_center = wrist_center
        prev_wrist_asymmetry = wrist_asymmetry

        bad_condition = (
                not all_tests_passed
                or hand_distance < HAND_MIN
                or hand_distance > HAND_MAX
        )

        if stage != "idle" and bad_condition:
            stage = "idle"
            start_counter = 0
            exercise_started = False

        # -----------------------------
        # Form statistics

        if exercise_started:
            total_frames += 1
            if all_tests_passed:
                correct_frames += 1

        accuracy = (
            (correct_frames / total_frames) * 100
            if total_frames > 0 else 0.0
        )

        # -----------------------------
        # Info panel

        cv.rectangle(frame, (0, 0), (320, 130), (0, 0, 0), -1)

        cv.putText(frame, f"Reps: {rep_count}", (15, 35),
                   cv.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        cv.putText(frame, f"Stage: {stage}", (15, 75),
                   cv.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        cv.putText(frame, f"Form: {accuracy:.1f}%", (15, 115),
                   cv.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

        # -----------------------------
        # Active warnings

        now = time.time()
        warning_y = 170
        expired = []

        for message, end_time in active_errors.items():

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

        for msg in expired:
            del active_errors[msg]

        # -----------------------------
        # Debug info

        cv.putText(
            frame,
            f"Height:{shoulder_elbow_diff:.3f} HandDistance:{hand_distance:.3f}",
            (15, frame.shape[0] - 20),
            cv.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1
        )

    cv.imshow("Front Bench Dips Counter", frame)

    if cv.waitKey(1) & 0xFF == 27:
        break

video.release()
cv.destroyAllWindows()