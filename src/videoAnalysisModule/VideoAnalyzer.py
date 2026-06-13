import cv2 as cv
import mediapipe as mp

from src.videoAnalysisModule.front_processor import FrontProcessor
from src.videoAnalysisModule.side_processor import SideProcessor


class VideoAnalyzer:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.mp_draw = mp.solutions.drawing_utils

        # POPRAWKA: Dwa osobne detektory zapobiegają gubieniu trackingu między klatkami Przód/Bok
        self.pose_detector_front = self.mp_pose.Pose(
            min_detection_confidence=0.5, min_tracking_confidence=0.5
        )
        self.pose_detector_side = self.mp_pose.Pose(
            min_detection_confidence=0.5, min_tracking_confidence=0.5
        )

        self.reset()

    def reset(self):
        self.front_proc = FrontProcessor()
        self.side_proc = SideProcessor()
        self.last_front_frame = None
        self.last_side_frame = None
        self.total_reps = 0

    def analyze_frame(self, frame, perspective="front"):
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

        # Synchronizacja liczników
        self.total_reps = max(self.front_proc.rep_count, self.side_proc.rep_count)

    def get_agr_frame(self, perspective="front"):
        if perspective == "front":
            return self.last_front_frame
        elif perspective == "side":
            return self.last_side_frame
        return None

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
        }
