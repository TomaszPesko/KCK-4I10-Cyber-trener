import time

import cv2 as cv
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from src.videoAnalysisModule.VideoAnalyzer import VideoAnalyzer


class VideoAnalysisThread(QThread):
    """Wątek odpowiedzialny za odtwarzanie i analizowanie filmów klatka po klatce."""

    frame_processed = Signal(
        object, object
    )  # (front_frame_or_none, side_frame_or_none)
    stats_updated = Signal(dict)
    finished_analysis = Signal(dict)

    def __init__(self, front_path=None, side_path=None):
        super().__init__()
        self.front_path = front_path
        self.side_path = side_path
        self._is_running = True
        self.analyzer = VideoAnalyzer()

    def run(self):
        cap_front = cv.VideoCapture(self.front_path) if self.front_path else None
        cap_side = cv.VideoCapture(self.side_path) if self.side_path else None

        self.analyzer.reset()

        while self._is_running:
            has_front, frame_front = cap_front.read() if cap_front else (False, None)
            has_side, frame_side = cap_side.read() if cap_side else (False, None)

            # Jeśli oba pliki się skończyły, przerywamy pętlę
            if not has_front and not has_side:
                break

            # Analiza przodu
            if has_front:
                self.analyzer.analyze_frame(frame_front, perspective="front")
            # Analiza boku
            if has_side:
                self.analyzer.analyze_frame(frame_side, perspective="side")

            # Pobieranie przetworzonych klatek AR
            out_front = self.analyzer.get_agr_frame("front") if has_front else None
            out_side = self.analyzer.get_agr_frame("side") if has_side else None

            current_info = self.analyzer.get_current_series_info()

            self.frame_processed.emit(out_front, out_side)
            self.stats_updated.emit(current_info)

            # Emulacja framerate (~30 FPS). W produkcji dostosuj do właściwości wideo
            time.sleep(0.033)

        if cap_front:
            cap_front.release()
        if cap_side:
            cap_side.release()

        # Przekaż końcowe statystyki serii
        self.finished_analysis.emit(self.analyzer.get_current_series_info())

    def stop(self):
        self._is_running = False
        self.wait()


class VideoDisplayWidget(QWidget):
    """Widget dzielący ekran (lub nie) i rysujący klatki z OpenCV (Numpy array)."""

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.lbl_front = QLabel("Oczekiwanie na wideo z przodu...")
        self.lbl_side = QLabel("Oczekiwanie na wideo z boku...")

        for lbl in [self.lbl_front, self.lbl_side]:
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                "background-color: #1a1a1a; border: 1px solid #333; color: #555;"
            )

            # --- KLUCZOWA POPRAWKA ---
            # Zmuszamy QLabel, by nie rósł razem z wkładanym do niego QPixmap
            lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

            layout.addWidget(lbl)

    def set_modes(self, show_front, show_side):
        self.lbl_front.setVisible(show_front)
        self.lbl_side.setVisible(show_side)
        self.clear_views()

    def clear_views(self):
        self.lbl_front.setText("Brak obrazu (Przód)")
        self.lbl_side.setText("Brak obrazu (Bok)")

    @Slot(object, object)
    def update_frames(self, front_img, side_img):
        if front_img is not None:
            self._convert_to_pixmap(front_img, self.lbl_front)
        if side_img is not None:
            self._convert_to_pixmap(side_img, self.lbl_side)

    def _convert_to_pixmap(self, cv_img, target_label):
        """Konwertuje tablicę BGR OpenCV na QPixmap i skaluje do wielkości lebelu."""
        # Bezpiecznik: jeśli widget został schowany lub ma zerową przestrzeń, pomiń
        if target_label.width() <= 10 or target_label.height() <= 10:
            return

        height, width, channel = cv_img.shape
        bytes_per_line = channel * width
        rgb_image = cv.cvtColor(cv_img, cv.COLOR_BGR2RGB)

        q_img = QImage(
            rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888
        )
        pixmap = QPixmap.fromImage(q_img)

        # Teraz pobieramy stabilny rozmiar kontenera, który nie rośnie w pętli
        scaled_pixmap = pixmap.scaled(
            target_label.width(),
            target_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        target_label.setPixmap(scaled_pixmap)
