import queue

import cv2 as cv
import mediapipe as mp

from src.include.set_data import Repetition, WorkoutSet
from src.videoAnalysisModule.front_processor import FrontProcessor
from src.videoAnalysisModule.side_processor import SideProcessor


class VideoAnalyzer:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.mp_draw = mp.solutions.drawing_utils

        self.pose_detector_front = self.mp_pose.Pose(
            min_detection_confidence=0.5, min_tracking_confidence=0.5
        )
        self.pose_detector_side = self.mp_pose.Pose(
            min_detection_confidence=0.5, min_tracking_confidence=0.5
        )

        self.front_queue = queue.Queue()
        self.side_queue = queue.Queue()

        self.cached_workout_set = None
        self.cached_bounds = None
        self.cached_paths = None

        self.reset()

    def reset(self):
        self.front_proc = FrontProcessor()
        self.side_proc = SideProcessor()
        self.last_front_frame = None
        self.last_side_frame = None

        self.total_reps = 0

        self.mismatch_detected = False
        self.stage_desync_counter = 0
        # Bardzo rygorystyczny próg desynchronizacji w trakcie ćwiczenia (0.5 sekundy)
        self.DESYNC_TOLERANCE_FRAMES = 15

    def is_sync_gesture_detected(
        self, frame, draw_frame=None, perspective="front"
    ) -> bool:
        """Bezstanowa funkcja do wykrywania gestu z opcją rysowania szkieletu do debugowania."""
        if frame is None:
            return False

        rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)

        detector = (
            self.pose_detector_front
            if perspective == "front"
            else self.pose_detector_side
        )
        res = detector.process(rgb)

        if not res.pose_landmarks:
            return False

        # --- NOWOŚĆ: Rysowanie szkieletu na ramce podglądu w celach debugowych ---
        if draw_frame is not None:
            self.mp_draw.draw_landmarks(
                draw_frame,
                res.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
            )

        l = res.pose_landmarks.landmark

        # Znajdujemy szczyt głowy
        head_points = [
            l[self.mp_pose.PoseLandmark.NOSE],
            l[self.mp_pose.PoseLandmark.LEFT_EAR],
            l[self.mp_pose.PoseLandmark.RIGHT_EAR],
        ]

        valid_head_points = [p.y for p in head_points if p.visibility > 0.4]
        if not valid_head_points:
            return False

        head_top_y = min(valid_head_points)

        VIS = 0.65

        r_wrist = l[self.mp_pose.PoseLandmark.RIGHT_WRIST]
        r_elbow = l[self.mp_pose.PoseLandmark.RIGHT_ELBOW]

        l_wrist = l[self.mp_pose.PoseLandmark.LEFT_WRIST]
        l_elbow = l[self.mp_pose.PoseLandmark.LEFT_ELBOW]

        r_raised = (
            r_wrist.visibility > VIS
            and r_elbow.visibility > VIS
            and r_wrist.y < head_top_y
            and r_wrist.y < r_elbow.y
        )

        l_raised = (
            l_wrist.visibility > VIS
            and l_elbow.visibility > VIS
            and l_wrist.y < head_top_y
            and l_wrist.y < l_elbow.y
        )

        return r_raised or l_raised

    def queue_frames(self, front_frame=None, side_frame=None):
        if front_frame is not None:
            self.front_queue.put(front_frame)
        if side_frame is not None:
            self.side_queue.put(side_frame)

    def process_next_synced_step(self):
        front_frame = self.front_queue.get() if not self.front_queue.empty() else None
        side_frame = self.side_queue.get() if not self.side_queue.empty() else None

        if front_frame is not None:
            self._analyze_perspective(front_frame, "front")
        if side_frame is not None:
            self._analyze_perspective(side_frame, "side")

        if front_frame is not None and side_frame is not None:
            if self.front_proc.stage != self.side_proc.stage:
                self.stage_desync_counter += 1
                if self.stage_desync_counter > self.DESYNC_TOLERANCE_FRAMES:
                    self.mismatch_detected = True
            else:
                self.stage_desync_counter = 0

        self.total_reps = max(self.front_proc.rep_count, self.side_proc.rep_count)
        return front_frame is not None or side_frame is not None

    def _analyze_perspective(self, frame, perspective):
        rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)

        if perspective == "front":
            self.last_front_frame = frame.copy()
            result = self.pose_detector_front.process(rgb)
            if result.pose_landmarks:
                self.mp_draw.draw_landmarks(
                    self.last_front_frame,
                    result.pose_landmarks,
                    self.mp_pose.POSE_CONNECTIONS,
                )
                self.last_front_frame = self.front_proc.process(
                    self.last_front_frame,
                    result.pose_landmarks.landmark,
                    self.mp_pose,
                    self.mp_draw,
                )
            else:
                self.front_proc.stage = "unknown"

        elif perspective == "side":
            self.last_side_frame = frame.copy()
            result = self.pose_detector_side.process(rgb)
            if result.pose_landmarks:
                self.mp_draw.draw_landmarks(
                    self.last_side_frame,
                    result.pose_landmarks,
                    self.mp_pose.POSE_CONNECTIONS,
                )
                self.last_side_frame = self.side_proc.process(
                    self.last_side_frame,
                    result.pose_landmarks.landmark,
                    self.mp_pose,
                    self.mp_draw,
                )
            else:
                self.side_proc.stage = "unknown"

    def get_agr_frame(self, perspective="front"):
        return self.last_front_frame if perspective == "front" else self.last_side_frame

    def get_current_series_info(self):
        return {
            "total_reps": self.total_reps,
            "front_reps": self.front_proc.rep_count,
            "side_reps": self.side_proc.rep_count,
            "front_stage": self.front_proc.stage,
            "side_stage": self.side_proc.stage,
            "hand_feedback": self.front_proc.hand_feedback,
            "leg_correct": self.side_proc.leg_correct,
            "body_correct": self.side_proc.body_correct,
            "mismatch_detected": self.mismatch_detected,
        }

    def _is_cache_valid(self, front_path, side_path, bounds_tuple) -> bool:
        return (
            self.cached_workout_set is not None
            and self.cached_paths == (front_path, side_path)
            and self.cached_bounds == bounds_tuple
        )

    def run_fast_background_analysis(
        self, front_path, side_path, f_start=0, f_end=0, s_start=0, s_end=0
    ) -> dict:
        cap_front = cv.VideoCapture(front_path) if front_path else None
        cap_side = cv.VideoCapture(side_path) if side_path else None

        if cap_front:
            cap_front.set(cv.CAP_PROP_POS_FRAMES, f_start)
        if cap_side:
            cap_side.set(cv.CAP_PROP_POS_FRAMES, s_start)

        self.reset()

        while True:
            curr_f = int(cap_front.get(cv.CAP_PROP_POS_FRAMES)) if cap_front else 0
            curr_s = int(cap_side.get(cv.CAP_PROP_POS_FRAMES)) if cap_side else 0

            has_front, frame_front = (
                cap_front.read() if (cap_front and curr_f <= f_end) else (False, None)
            )
            has_side, frame_side = (
                cap_side.read() if (cap_side and curr_s <= s_end) else (False, None)
            )

            if not has_front and not has_side:
                break

            self.queue_frames(frame_front, frame_side)
            self.process_next_synced_step()

        if cap_front:
            cap_front.release()
        if cap_side:
            cap_side.release()

        bounds_tuple = (f_start, f_end, s_start, s_end)
        workout_set = self.compile_and_cache_workout_set(
            front_path, side_path, bounds_tuple
        )

        return {"workout_set": workout_set, "mismatch": self.mismatch_detected}

    def get_or_analyze_workout_set(
        self,
        front_path,
        side_path,
        f_start=0,
        f_end=0,
        s_start=0,
        s_end=0,
        force_reanalyze=False,
    ) -> dict:
        bounds_tuple = (f_start, f_end, s_start, s_end)

        if not force_reanalyze and self._is_cache_valid(
            front_path, side_path, bounds_tuple
        ):
            return {
                "workout_set": self.cached_workout_set,
                "mismatch": self.mismatch_detected,
            }

        return self.run_fast_background_analysis(
            front_path, side_path, f_start, f_end, s_start, s_end
        )

    def compile_and_cache_workout_set(
        self, front_path, side_path, bounds_tuple
    ) -> WorkoutSet:
        info = self.get_current_series_info()
        workout_set = WorkoutSet(location="None", duration=info["total_reps"] * 2)

        for _ in range(info["total_reps"]):
            is_shallow = not info["leg_correct"]
            is_far = info["hand_feedback"] != "OK"
            is_tempo = not info["body_correct"]
            quality = "Faulty" if (is_shallow or is_far or is_tempo) else "Correct"

            rep_obj = Repetition(
                speed=2.2,
                quality=quality,
                shallow=is_shallow,
                far=is_far,
                tempo=is_tempo,
            )
            rep_obj.error_too_shallow = is_shallow
            rep_obj.error_too_far_from_chair = is_far
            rep_obj.error_lacks_tempo_control = is_tempo
            workout_set.add_repetition(rep_obj)

        self.cached_workout_set = workout_set
        self.cached_paths = (front_path, side_path)
        self.cached_bounds = bounds_tuple

        return workout_set
