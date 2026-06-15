import time
import cv2 as cv
from PySide6.QtCore import QThread, Signal


class CameraPreviewThread(QThread):
    frame_processed = Signal(object, object)

    def __init__(self, front_index=0, side_index=1, has_front=True, has_side=True):
        super().__init__()
        self.front_index = front_index
        self.side_index = side_index
        self.has_front = has_front
        self.has_side = has_side
        self._is_running = True

    def run(self):
        cap_front = cv.VideoCapture(self.front_index) if self.has_front else None
        cap_side = cv.VideoCapture(self.side_index) if self.has_side else None

        while self._is_running:
            has_f, frame_front = cap_front.read() if cap_front else (False, None)
            has_s, frame_side = cap_side.read() if cap_side else (False, None)

            display_front = frame_front.copy() if has_f else None
            display_side = frame_side.copy() if has_s else None

            self.frame_processed.emit(display_front, display_side)
            time.sleep(0.033)

        if cap_front:
            cap_front.release()
        if cap_side:
            cap_side.release()

    def stop(self):
        self._is_running = False
        self.wait()
