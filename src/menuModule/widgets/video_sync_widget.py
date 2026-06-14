# ==> ./menuModule/widgets/video_sync_widget.py <==
# ==> ./menuModule/widgets/video_sync_widget.py <==
import cv2 as cv
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class VideoSyncWidget(QWidget):
    """Widżet synchronizacji wideo wyrównany do góry z kontrolą początku i końca serii."""

    def __init__(self):
        super().__init__()
        self.front_cap = None
        self.side_cap = None
        self.front_total_frames = 0
        self.side_total_frames = 0

        self._init_ui()

    def _init_ui(self):
        # Wyrównanie całego kontenera głównego do samej góry przestrzeni
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)
        main_layout.setAlignment(Qt.AlignTop)

        title = QLabel("Podgląd i Synchronizacja Materiału Wideo")
        title.setStyleSheet(
            "color: #00cc66; font-size: 16px; font-weight: bold; margin-bottom: 5px;"
        )
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Siatka QGridLayout zapewniająca idealne proporcje 50/50 kolumn
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)

        # --- PERSPEKTYWA Z PRZODU ---
        front_container = QWidget()
        front_layout = QVBoxLayout(front_container)
        front_layout.setContentsMargins(0, 0, 0, 0)
        front_layout.setAlignment(Qt.AlignTop)

        self.lbl_front_title = QLabel("Perspektywa z przodu (Brak pliku)")
        self.lbl_front_title.setStyleSheet("color: #dddddd; font-weight: bold;")
        self.lbl_front_title.setAlignment(Qt.AlignCenter)

        self.lbl_front_preview = QLabel()
        self.lbl_front_preview.setAlignment(Qt.AlignCenter)
        self.lbl_front_preview.setStyleSheet(
            "background-color: #1a1a1a; border: 1px solid #333; border-radius: 6px;"
        )
        self.lbl_front_preview.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self.lbl_front_preview.setMinimumHeight(280)

        front_controls = QGridLayout()
        front_controls.addWidget(QLabel("Początek serii:"), 0, 0)
        self.slider_front_start = QSlider(Qt.Horizontal)
        self.slider_front_start.setEnabled(False)
        self.slider_front_start.valueChanged.connect(self._on_front_start_changed)
        front_controls.addWidget(self.slider_front_start, 0, 1)

        front_controls.addWidget(QLabel("Koniec serii:"), 1, 0)
        self.slider_front_end = QSlider(Qt.Horizontal)
        self.slider_front_end.setEnabled(False)
        self.slider_front_end.valueChanged.connect(self._on_front_end_changed)
        front_controls.addWidget(self.slider_front_end, 1, 1)

        front_layout.addWidget(self.lbl_front_title)
        front_layout.addWidget(self.lbl_front_preview)
        front_layout.addThemeLayout = front_layout.addLayout(front_controls)

        # --- PERSPEKTYWA Z BOKU ---
        side_container = QWidget()
        side_layout = QVBoxLayout(side_container)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setAlignment(Qt.AlignTop)

        self.lbl_side_title = QLabel("Perspektywa z boku (Brak pliku)")
        self.lbl_side_title.setStyleSheet("color: #dddddd; font-weight: bold;")
        self.lbl_side_title.setAlignment(Qt.AlignCenter)

        self.lbl_side_preview = QLabel()
        self.lbl_side_preview.setAlignment(Qt.AlignCenter)
        self.lbl_side_preview.setStyleSheet(
            "background-color: #1a1a1a; border: 1px solid #333; border-radius: 6px;"
        )
        self.lbl_side_preview.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self.lbl_side_preview.setMinimumHeight(280)

        side_controls = QGridLayout()
        side_controls.addWidget(QLabel("Początek serii:"), 0, 0)
        self.slider_side_start = QSlider(Qt.Horizontal)
        self.slider_side_start.setEnabled(False)
        self.slider_side_start.valueChanged.connect(self._on_side_start_changed)
        side_controls.addWidget(self.slider_side_start, 0, 1)

        side_controls.addWidget(QLabel("Koniec serii:"), 1, 0)
        self.slider_side_end = QSlider(Qt.Horizontal)
        self.slider_side_end.setEnabled(False)
        self.slider_side_end.valueChanged.connect(self._on_side_end_changed)
        side_controls.addWidget(self.slider_side_end, 1, 1)

        side_layout.addWidget(self.lbl_side_title)
        side_layout.addWidget(self.lbl_side_preview)
        side_layout.addLayout(side_controls)

        # Montaż kolumn 50/50 w siatce
        grid_layout.addWidget(front_container, 0, 0)
        grid_layout.addWidget(side_container, 0, 1)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)

        main_layout.addLayout(grid_layout)

    def load_videos(self, front_path, side_path):
        self._release_caps()

        if front_path:
            self.front_cap = cv.VideoCapture(front_path)
            self.front_total_frames = int(self.front_cap.get(cv.CAP_PROP_FRAME_COUNT))
            self.slider_front_start.setRange(0, self.front_total_frames - 2)
            self.slider_front_end.setRange(1, self.front_total_frames - 1)
            self.slider_front_start.setValue(0)
            self.slider_front_end.setValue(self.front_total_frames - 1)
            self.slider_front_start.setEnabled(True)
            self.slider_front_end.setEnabled(True)
            self._update_front_preview(0)
        else:
            self.lbl_front_preview.setPixmap(QPixmap())
            self.lbl_front_preview.setText("Nie wybrano wideo z przodu")
            self.slider_front_start.setEnabled(False)
            self.slider_front_end.setEnabled(False)

        if side_path:
            self.side_cap = cv.VideoCapture(side_path)
            self.side_total_frames = int(self.side_cap.get(cv.CAP_PROP_FRAME_COUNT))
            self.slider_side_start.setRange(0, self.side_total_frames - 2)
            self.slider_side_end.setRange(1, self.side_total_frames - 1)
            self.slider_side_start.setValue(0)
            self.slider_side_end.setValue(self.side_total_frames - 1)
            self.slider_side_start.setEnabled(True)
            self.slider_side_end.setEnabled(True)
            self._update_side_preview(0)
        else:
            self.lbl_side_preview.setPixmap(QPixmap())
            self.lbl_side_preview.setText("Nie wybrano wideo z boku")
            self.slider_side_start.setEnabled(False)
            self.slider_side_end.setEnabled(False)

    def _on_front_start_changed(self, val):
        if val >= self.slider_front_end.value():
            self.slider_front_start.setValue(self.slider_front_end.value() - 1)
            return
        self._update_front_preview(val)

    def _on_front_end_changed(self, val):
        if val <= self.slider_front_start.value():
            self.slider_front_end.setValue(self.slider_front_start.value() + 1)
            return
        self._update_front_preview(val)

    def _on_side_start_changed(self, val):
        if val >= self.slider_side_end.value():
            self.slider_side_start.setValue(self.slider_side_end.value() - 1)
            return
        self._update_side_preview(val)

    def _on_side_end_changed(self, val):
        if val <= self.slider_side_start.value():
            self.slider_side_end.setValue(self.slider_side_start.value() + 1)
            return
        self._update_side_preview(val)

    def _update_front_preview(self, frame_idx):
        if self.front_cap:
            self.front_cap.set(cv.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = self.front_cap.read()
            if ret:
                self._display_frame(frame, self.lbl_front_preview)
            self.lbl_front_title.setText(
                f"Przód (Start: {self.slider_front_start.value()} | Koniec: {self.slider_front_end.value()})"
            )

    def _update_side_preview(self, frame_idx):
        if self.side_cap:
            self.side_cap.set(cv.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = self.side_cap.read()
            if ret:
                self._display_frame(frame, self.lbl_side_preview)
            self.lbl_side_title.setText(
                f"Bok (Start: {self.slider_side_start.value()} | Koniec: {self.slider_side_end.value()})"
            )

    def _display_frame(self, cv_img, target_label):
        target_w = target_label.width()
        target_h = target_label.height()
        if target_w <= 10 or target_h <= 10:
            return
        rgb_image = cv.cvtColor(cv_img, cv.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img).scaled(
            target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        target_label.setPixmap(pixmap)

    def get_bounds(self):
        f_start = (
            self.slider_front_start.value()
            if self.slider_front_start.isEnabled()
            else 0
        )
        f_end = (
            self.slider_front_end.value() if self.slider_front_end.isEnabled() else 0
        )
        s_start = (
            self.slider_side_start.value() if self.slider_side_start.isEnabled() else 0
        )
        s_end = self.slider_side_end.value() if self.slider_side_end.isEnabled() else 0
        return f_start, f_end, s_start, s_end

    def restore_bounds(self, f_start, f_end, s_start, s_end):
        """Przywraca i blokuje suwaki na pozycjach wybranych przed restartem deskryptorów plików."""
        if self.front_cap:
            self.slider_front_start.setValue(min(f_start, self.front_total_frames - 2))
            self.slider_front_end.setValue(min(f_end, self.front_total_frames - 1))
            self._update_front_preview(f_start)
        if self.side_cap:
            self.slider_side_start.setValue(min(s_start, self.side_total_frames - 2))
            self.slider_side_end.setValue(min(s_end, self.side_total_frames - 1))
            self._update_side_preview(s_start)

    def _release_caps(self):
        if self.front_cap:
            self.front_cap.release()
            self.front_cap = None
        if self.side_cap:
            self.side_cap.release()
            self.side_cap = None
