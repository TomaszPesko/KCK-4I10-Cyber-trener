import cv2 as cv
import mediapipe as mp

mp_pose_module = mp.solutions.pose
mp_utils = mp.solutions.drawing_utils

video = cv.VideoCapture("letters.mp4")
pose_estimator = mp_pose_module.Pose()


def aligned_horiz(a, b, c, tol=0.05):
    return max(abs(a.y - b.y), abs(b.y - c.y)) < tol


def strictly_desc(a, b, c, tol=0.05):
    return (a.y - b.y) > tol and (b.y - c.y) > tol


def strictly_asc(a, b, c, tol=0.05):
    return (b.y - a.y) > tol and (c.y - b.y) > tol


def classify_pose(points, tol_horiz=0.05, tol_vert=0.05):
    left_s = points[mp_pose_module.PoseLandmark.LEFT_SHOULDER]
    right_s = points[mp_pose_module.PoseLandmark.RIGHT_SHOULDER]
    left_e = points[mp_pose_module.PoseLandmark.LEFT_ELBOW]
    right_e = points[mp_pose_module.PoseLandmark.RIGHT_ELBOW]
    left_w = points[mp_pose_module.PoseLandmark.LEFT_WRIST]
    right_w = points[mp_pose_module.PoseLandmark.RIGHT_WRIST]

    left_line = aligned_horiz(left_w, left_e, left_s, tol_horiz)
    right_line = aligned_horiz(right_w, right_e, right_s, tol_horiz)

    if left_line and right_line:
        return "T"

    if strictly_desc(left_w, left_e, left_s, tol_vert) and strictly_desc(
        right_w, right_e, right_s, tol_vert
    ):
        return "I"

    if strictly_asc(left_w, left_e, left_s, tol_vert) and strictly_asc(
        right_w, right_e, right_s, tol_vert
    ):
        return "Y"

    if strictly_asc(right_w, right_e, right_s, tol_vert) and left_line:
        return "L"

    return ""


tolerance_horizontal = 0.05
tolerance_vertical = 0.05

while video.isOpened():
    ok, img = video.read()
    if not ok:
        break

    img_rgb = cv.cvtColor(img, cv.COLOR_BGR2RGB)
    pose_result = pose_estimator.process(img_rgb)

    detected = ""

    if pose_result.pose_landmarks is not None:
        pts = pose_result.pose_landmarks.landmark
        detected = classify_pose(
            pts, tol_horiz=tolerance_horizontal, tol_vert=tolerance_vertical
        )
        mp_utils.draw_landmarks(
            img, pose_result.pose_landmarks, mp_pose_module.POSE_CONNECTIONS
        )

    cv.putText(img, detected, (50, 100), cv.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 3)
    cv.imshow("Pose detection", img)

    if cv.waitKey(1) & 0xFF == 27:
        break

video.release()
cv.destroyAllWindows()
