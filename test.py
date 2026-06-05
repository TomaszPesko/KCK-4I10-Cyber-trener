import math

import cv2 as cv
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# ------------------------------------------------------------------
# Konfiguracja MediaPipe Tasks (Nowe API)
# ------------------------------------------------------------------
model_path = "pose_landmarker_full.task"  # Pobierz ten plik ze strony MediaPipe!

BaseOptions = mp.tasks.BaseOptions
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

options = PoseLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=model_path),
    running_mode=VisionRunningMode.VIDEO,
)

# Indeksy punktów w nowym API (odpowiadają starym PoseLandmark)
RIGHT_SHOULDER = 12
RIGHT_ELBOW = 14
RIGHT_WRIST = 16
LEFT_WRIST = 15

# Video
video = cv.VideoCapture("benchdipfrontdemo.mp4")


def distance(a, b):
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


# Repetition variables
rep_count = 0
stage = "up"

# Thresholds
DOWN_THRESHOLD = 0.04
UP_THRESHOLD = 0.10
HAND_MIN = 0.18
HAND_MAX = 0.42

# Uruchomienie detektora przy użyciu kontekstu 'with'
with PoseLandmarker.create_from_options(options) as landmarker:

    while video.isOpened():
        ok, frame = video.read()
        if not ok:
            break

        # MediaPipe Tasks wymaga formatu RGB i obiektu mp.Image
        rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        # W trybie VIDEO wymagane jest podanie znacznika czasu w milisekundach
        frame_timestamp_ms = int(video.get(cv.CAP_PROP_POS_MSEC))

        # Detekcja postawy
        result = landmarker.detect_for_video(mp_image, frame_timestamp_ms)

        if result.pose_landmarks:
            # W nowym API wyniki są listą list (obsługa wielu osób, bierzemy pierwszą [0])
            landmarks = result.pose_landmarks[0]

            # Pobranie punktów
            right_shoulder = landmarks[RIGHT_SHOULDER]
            right_elbow = landmarks[RIGHT_ELBOW]
            right_wrist = landmarks[RIGHT_WRIST]
            left_wrist = landmarks[LEFT_WRIST]

            # -----------------------------
            # Logika analizy ruchu

            # Główny parametr wysokości
            shoulder_elbow_diff = abs(right_shoulder.y - right_elbow.y)

            # Nadgarstek musi być poniżej łokcia
            proper_arm = right_wrist.y > right_elbow.y

            # Walidacja rozstawu dłoni
            hand_distance = distance(left_wrist, right_wrist)
            hands_ok = HAND_MIN <= hand_distance <= HAND_MAX

            # -----------------------------
            # Rysowanie szkieletu (ręcznie za pomocą OpenCV)
            h, w, _ = frame.shape
            points_to_draw = [RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST, LEFT_WRIST]

            # Rysowanie kropek dla kluczowych stawów
            for idx in points_to_draw:
                lm = landmarks[idx]
                cx, cy = int(lm.x * w), int(lm.y * h)
                cv.circle(frame, (cx, cy), 6, (0, 255, 255), -1)

            # Połączenie punktów prawej ręki (bark -> łokieć -> nadgarstek)
            s_pos = (int(right_shoulder.x * w), int(right_shoulder.y * h))
            e_pos = (int(right_elbow.x * w), int(right_elbow.y * h))
            w_pos = (int(right_wrist.x * w), int(right_wrist.y * h))
            cv.line(frame, s_pos, e_pos, (255, 0, 0), 3)
            cv.line(frame, e_pos, w_pos, (255, 0, 0), 3)

            # -----------------------------
            # Logika powtórzeń
            if hands_ok and proper_arm:
                # Dolna pozycja
                if shoulder_elbow_diff < DOWN_THRESHOLD:
                    stage = "down"
                # Powrót do góry
                elif shoulder_elbow_diff > UP_THRESHOLD and stage == "down":
                    rep_count += 1
                    stage = "up"

            # Informacja zwrotna o dłoniach
            hand_feedback = "OK"
            if hand_distance < HAND_MIN:
                hand_feedback = "Too narrow"
            elif hand_distance > HAND_MAX:
                hand_feedback = "Too wide"

            # Panel informacyjny (UI)
            cv.rectangle(frame, (0, 0), (520, 220), (0, 0, 0), -1)

            cv.putText(
                frame,
                f"Reps: {rep_count}",
                (20, 40),
                cv.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )
            cv.putText(
                frame,
                f"Stage: {stage}",
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

            feedback_color = (0, 255, 0) if hand_feedback == "OK" else (0, 0, 255)
            cv.putText(
                frame,
                f"Hands: {hand_feedback}",
                (20, 200),
                cv.FONT_HERSHEY_SIMPLEX,
                0.9,
                feedback_color,
                2,
            )

        cv.imshow("Front Bench Dips Counter", frame)

        if cv.waitKey(1) & 0xFF == 27:  # klawisz ESC
            break

video.release()
cv.destroyAllWindows()
