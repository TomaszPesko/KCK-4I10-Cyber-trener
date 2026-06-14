import queue

import cv2 as cv
import mediapipe as mp

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

        # Synchronization Queues (Future-proofing for Live Camera feeds)
        self.front_queue = queue.Queue()
        self.side_queue = queue.Queue()

        self.reset()

    def reset(self):
        self.front_proc = FrontProcessor()
        self.side_proc = SideProcessor()
        self.last_front_frame = None
        self.last_side_frame = None
        self.total_reps = 0

        # Mismatch detection tracking
        self.mismatch_detected = False
        self.stage_desync_counter = (
            0  # Counts frames where stages completely oppose each other
        )
        self.DESYNC_TOLERANCE_FRAMES = 90  # ~3 seconds at 30fps

    def queue_frames(self, front_frame=None, side_frame=None):
        """Pushes incoming frames into synchronized queues."""
        if front_frame is not None:
            self.front_queue.put(front_frame)
        if side_frame is not None:
            self.side_queue.put(side_frame)

    def process_next_synced_step(self):
        """Pops available frames from queues and processes them together."""
        front_frame = self.front_queue.get() if not self.front_queue.empty() else None
        side_frame = self.side_queue.get() if not self.side_queue.empty() else None

        if front_frame is not None:
            self._analyze_perspective(front_frame, "front")
        if side_frame is not None:
            self._analyze_perspective(side_frame, "side")

        # Synchronization & Mismatch Logic:
        # If both perspectives are active but report wildly different movement stages for too long
        if front_frame is not None and side_frame is not None:
            if self.front_proc.stage != self.side_proc.stage:
                self.stage_desync_counter += 1
                if self.stage_desync_counter > self.DESYNC_TOLERANCE_FRAMES:
                    self.mismatch_detected = True
            else:
                self.stage_desync_counter = 0  # Reset on sync recovery

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
            "mismatch_detected": self.mismatch_detected,  # New flag
        }
