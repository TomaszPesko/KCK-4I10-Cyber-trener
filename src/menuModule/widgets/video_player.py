import time

import cv2 as cv
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from src.include.set_data import Repetition, WorkoutSet
from src.videoAnalysisModule.VideoAnalyzer import VideoAnalyzer


class VideoAnalysisThread(QThread):
    frame_processed = Signal(object, object)
    stats_updated = Signal(dict)
    finished_analysis = Signal(dict)

    def __init__(
        self,
        shared_analyzer: VideoAnalyzer,
        front_path=None,
        side_path=None,
        f_start=0,
        f_end=0,
        s_start=0,
        s_end=0,
    ):
        super().__init__()
        self.analyzer = shared_analyzer
        self.front_path = front_path
        self.side_path = side_path
        self.f_start = f_start
        self.f_end = f_end
        self.s_start = s_start
        self.s_end = s_end
        self._is_running = True

    def run(self):
        cap_front = cv.VideoCapture(self.front_path) if self.front_path else None
        cap_side = cv.VideoCapture(self.side_path) if self.side_path else None

        if cap_front:
            cap_front.set(cv.CAP_PROP_POS_FRAMES, self.f_start)
        if cap_side:
            cap_side.set(cv.CAP_PROP_POS_FRAMES, self.s_start)

        self.analyzer.reset()

        while self._is_running:
            current_f = int(cap_front.get(cv.CAP_PROP_POS_FRAMES)) if cap_front else 0
            current_s = int(cap_side.get(cv.CAP_PROP_POS_FRAMES)) if cap_side else 0

            has_front, frame_front = (
                cap_front.read()
                if (cap_front and current_f <= self.f_end)
                else (False, None)
            )
            has_side, frame_side = (
                cap_side.read()
                if (cap_side and current_s <= self.s_end)
                else (False, None)
            )

            if not has_front and not has_side:
                break

            self.analyzer.queue_frames(frame_front, frame_side)
            self.analyzer.process_next_synced_step()

            out_front = self.analyzer.get_agr_frame("front")
            out_side = self.analyzer.get_agr_frame("side")
            current_info = self.analyzer.get_current_series_info()

            self.frame_processed.emit(out_front, out_side)
            self.stats_updated.emit(current_info)

            time.sleep(0.033)

        if cap_front:
            cap_front.release()
        if cap_side:
            cap_side.release()

        # Odtwarzacz AR również zapisuje gotowy skompilowany obiekt bezpośrednio do cache silnika
        bounds_tuple = (self.f_start, self.f_end, self.s_start, self.s_end)
        self.analyzer.compile_and_cache_workout_set(
            self.front_path, self.side_path, bounds_tuple
        )

        self.finished_analysis.emit(self.analyzer.get_current_series_info())

    def stop(self):
        self._is_running = False
        self.wait()


class VideoDisplayWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.lbl_front = QLabel("Awaiting front view video feed...")
        self.lbl_side = QLabel("Awaiting side view video feed...")

        for lbl in [self.lbl_front, self.lbl_side]:
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                "background-color: #1a1a1a; border: 1px solid #333; color: #555;"
            )
            lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
            layout.addWidget(lbl)

    def set_modes(self, show_front, show_side):
        self.lbl_front.setVisible(show_front)
        self.lbl_side.setVisible(show_side)
        self.clear_views()

    def clear_views(self):
        self.lbl_front.setText("No feed source (Front)")
        self.lbl_side.setText("No feed source (Side)")

    @Slot(object, object)
    def update_frames(self, front_img, side_img):
        if front_img is not None:
            self._convert_to_pixmap(front_img, self.lbl_front)
        if side_img is not None:
            self._convert_to_pixmap(side_img, self.lbl_side)

    def _convert_to_pixmap(self, cv_img, target_label):
        if target_label.width() <= 10 or target_label.height() <= 10:
            return

        height, width, channel = cv_img.shape
        bytes_per_line = channel * width
        rgb_image = cv.cvtColor(cv_img, cv.COLOR_BGR2RGB)

        q_img = QImage(
            rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888
        )
        pixmap = QPixmap.fromImage(q_img)

        scaled_pixmap = pixmap.scaled(
            target_label.width(),
            target_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        target_label.setPixmap(scaled_pixmap)
