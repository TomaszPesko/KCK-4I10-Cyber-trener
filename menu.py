import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsBlurEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# ===== TEMPLATE =====


class TemplateWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("E-trener")

        screen = QApplication.primaryScreen().geometry()
        self.resize(int(screen.width() * 0.8), int(screen.height() * 0.8))

        # ===== BACKGROUND =====
        self.bg_label = QLabel(self)
        self.bg_label.setScaledContents(True)
        pixmap = QPixmap("gui_background.jpeg")
        self.bg_label.setPixmap(pixmap)

        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(20)  # siła rozmycia
        self.bg_label.setGraphicsEffect(blur)

        # ===== MAIN LAYOUT =====
        self.main_container = QWidget(self)
        main_layout = QHBoxLayout(self.main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ===== LEFT MENU (30%) =====
        self.menu_wrapper = QWidget()
        self.menu_wrapper.setFixedWidth(int(self.width() * 0.3))

        wrapper_layout = QVBoxLayout(self.menu_wrapper)
        wrapper_layout.setContentsMargins(20, 20, 20, 20)

        self.menu_card = QFrame()
        self.menu_card.setObjectName("menuCard")

        self.menu_layout = QVBoxLayout(self.menu_card)
        self.menu_layout.setSpacing(15)
        self.menu_layout.setContentsMargins(20, 20, 20, 20)

        wrapper_layout.addWidget(self.menu_card)

        # ===== RIGHT CONTENT =====
        self.content = QFrame()
        self.content.setObjectName("contentArea")

        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(20, 20, 20, 20)

        main_layout.addWidget(self.menu_wrapper)
        main_layout.addWidget(self.content)

        # ===== STYLE =====
        self.setStyleSheet("""
        QWidget {
            background: transparent;
        }

        #menuCard {
            background-color: rgba(80, 80, 80, 200);
            border-radius: 20px;
        }

        QPushButton {
            background-color: rgba(60, 60, 60, 220);
            color: white;
            border-radius: 10px;
            padding: 10px;
            text-align: left;
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

    # ===== RESIZE =====
    def resizeEvent(self, event):
        self.bg_label.setGeometry(self.rect())
        self.main_container.setGeometry(self.rect())
        super().resizeEvent(event)

    # ===== API =====

    def add_menu_option(self, text, callback):
        """
        callback = funkcja pythonowa (np. lambda, metoda klasy)
        """
        btn = QPushButton(text)

        # ===== Qt signal-slot =====
        btn.clicked.connect(callback)

        self.menu_layout.addWidget(btn)

    def set_content(self, widget):
        for i in reversed(range(self.content_layout.count())):
            self.content_layout.itemAt(i).widget().deleteLater()

        self.content_layout.addWidget(widget)


# ===== DEMO =====


class DemoApp(TemplateWindow):
    def __init__(self):
        super().__init__()

        self.add_menu_option("Dodaj serię", lambda: self.show_page("Dodaj serię"))
        self.add_menu_option("Wczytaj serię", lambda: self.show_page("Wczytaj serię"))
        self.add_menu_option("Statystyki", lambda: self.show_page("Statystyki"))
        self.add_menu_option("Progres", lambda: self.show_page("Progres"))
        self.add_menu_option("Nowe okno", self.open_new_window)
        self.add_menu_option("Wyjście", self.close)

        self.show_page("Start")

    def show_page(self, text):
        page = QWidget()
        layout = QVBoxLayout(page)

        label = QLabel(text)
        label.setStyleSheet("color: white; font-size: 24px;")
        label.setAlignment(Qt.AlignCenter)

        layout.addWidget(label)

        self.set_content(page)

    def open_new_window(self):
        self.new_window = QWidget()
        self.new_window.setWindowTitle("Nowe okno")
        self.new_window.resize(400, 300)

        layout = QVBoxLayout(self.new_window)
        layout.addWidget(QLabel("To jest nowe okno"))

        self.new_window.show()


# ===== START =====

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DemoApp()
    window.show()
    sys.exit(app.exec())
