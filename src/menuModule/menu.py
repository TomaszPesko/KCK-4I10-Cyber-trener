import os
import sys

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsBlurEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.voiceSynthesisModule.VoiceSynthesizer import VoiceSynthesizer


def get_resource_path(relative_path):
    """Zwraca absolutną ścieżkę do zasobów. Kompatybilne z deweloperką i PyInstallerem."""
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class HoverSoundButton(QPushButton):
    """Przycisk rozszerzony o natywne przechwytywanie zdarzenia najechania kursorem."""

    def __init__(self, text, voice_instance: VoiceSynthesizer, parent=None):
        super().__init__(text, parent)
        self.voice = voice_instance

    def enterEvent(self, event):
        """Wywoływane automatycznie, gdy myszka wkracza na obszar przycisku."""
        if self.isEnabled():
            self.voice.play_hover_sound()
        super().enterEvent(event)


class Screen:
    def __init__(self, content_widget: QWidget):
        self.content_widget = content_widget
        self.options = []

    def add_option(self, text: str, callback):
        self.options.append((text, callback))


class AppWindow(QWidget):
    def __init__(self, title="Aplikacja", bg_image_path=None):
        super().__init__()
        self.setWindowTitle(title)

        if bg_image_path is None:
            bg_image_path = get_resource_path("resources/gui_background.jpeg")
        self.voice = VoiceSynthesizer()

        screen_geom = QApplication.primaryScreen().geometry()
        self.resize(int(screen_geom.width() * 0.8), int(screen_geom.height() * 0.8))
        self.setMinimumSize(900, 600)

        self._screens = {}

        self.bg_label = QLabel(self)
        self.bg_label.setScaledContents(True)
        if bg_image_path:
            self.bg_label.setPixmap(QPixmap(bg_image_path))
        else:
            print(f"[Warning] Nie znaleziono tła pod ścieżką: {bg_image_path}")

        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(20)
        self.bg_label.setGraphicsEffect(blur)

        self.main_container = QWidget(self)
        root_layout = QHBoxLayout(self.main_container)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self.split_layout = QHBoxLayout()
        self.split_layout.setSpacing(10)
        root_layout.addLayout(self.split_layout)

        self.menu_wrapper = QWidget()
        self.menu_wrapper.setMinimumWidth(220)
        self.menu_wrapper.setMaximumWidth(380)

        self.wrapper_layout = QVBoxLayout(self.menu_wrapper)
        self.menu_stack = QStackedWidget()
        self.wrapper_layout.addWidget(self.menu_stack, alignment=Qt.AlignTop)

        self.content_frame = QFrame()
        self.content_frame.setObjectName("contentArea")

        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(20, 20, 20, 20)

        self.content_stack = QStackedWidget()
        self.content_layout.addWidget(self.content_stack)

        self.split_layout.addWidget(self.menu_wrapper, stretch=3)
        self.split_layout.addWidget(self.content_frame, stretch=7)

        self.setStyleSheet("""
        QWidget { background: transparent; }
        #menuCard {
            background-color: rgba(80, 80, 80, 200);
            border-radius: 20px;
        }
        QPushButton {
            background-color: rgba(60, 60, 60, 220);
            color: white;
            border-radius: 10px;
            padding: 8px;
            text-align: left;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #00cc66;
            color: black;
        }
        #contentArea {
            background-color: rgba(30, 30, 30, 220);
            border-radius: 10px;
        }
        """)

    def resizeEvent(self, event):
        self.bg_label.setGeometry(self.rect())
        self.main_container.setGeometry(self.rect())
        w, h = self.width(), self.height()
        pad_w, pad_h = int(w * 0.02), int(h * 0.03)
        self.wrapper_layout.setContentsMargins(pad_w, pad_h, pad_w, pad_h)
        self.split_layout.setContentsMargins(pad_w, pad_h, pad_w, pad_h)

        for i in range(self.menu_stack.count()):
            card = self.menu_stack.widget(i)
            if card and card.layout():
                card.layout().setContentsMargins(pad_w, pad_h, pad_w, pad_h)
        super().resizeEvent(event)

    def register_screen(self, name: str, screen: Screen):
        menu_card = QFrame()
        menu_card.setObjectName("menuCard")
        menu_card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        card_layout = QVBoxLayout(menu_card)
        card_layout.setSpacing(8)

        for text, callback in screen.options:
            # Użycie nowego typu przycisku z obsługą dźwięku Hover
            btn = HoverSoundButton(text, self.voice)
            btn.clicked.connect(callback)
            card_layout.addWidget(btn)

        self.menu_stack.addWidget(menu_card)
        self.content_stack.addWidget(screen.content_widget)
        self._screens[name] = self.menu_stack.count() - 1

    def switch_to_screen(self, name: str):
        if name in self._screens:
            idx = self._screens[name]
            self.menu_stack.setCurrentIndex(idx)
            self.content_stack.setCurrentIndex(idx)

    def refresh_screen_menu(self, name: str, screen: Screen):
        if name in self._screens:
            idx = self._screens[name]
            menu_card = self.menu_stack.widget(idx)

            if menu_card and menu_card.layout():
                layout = menu_card.layout()
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()

                for text, callback in screen.options:
                    btn = HoverSoundButton(text, self.voice)
                    btn.clicked.connect(callback)
                    layout.addWidget(btn)
