from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from src.menuModule.menu import Screen


class BaseScreen(Screen):
    """Pomocnicza klasa bazowa ułatwiająca tworzenie powtarzalnych layoutów."""

    def __init__(self, title: str, subtitle: str):
        self.container = QWidget()
        layout = QVBoxLayout(self.container)
        layout.setAlignment(Qt.AlignCenter)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(
            "color: #00cc66; font-size: 28px; font-weight: bold; margin-bottom: 10px;"
        )
        lbl_title.setAlignment(Qt.AlignCenter)

        lbl_sub = QLabel(subtitle)
        lbl_sub.setStyleSheet("color: #dddddd; font-size: 16px;")
        lbl_sub.setAlignment(Qt.AlignCenter)

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_sub)
        super().__init__(self.container)
