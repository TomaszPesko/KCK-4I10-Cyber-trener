import sys
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
)
from PySide6.QtCore import Qt

# ===== TEMPLATE =====


class TemplateWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("E-trener")

        # rozmiar ~80% ekranu
        screen = QApplication.primaryScreen().geometry()
        self.resize(int(screen.width() * 0.8), int(screen.height() * 0.8))

        # ===== MAIN LAYOUT =====
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ===== LEFT MENU (30%) =====
        self.menu_wrapper = QWidget()
        self.menu_wrapper.setFixedWidth(int(self.width() * 0.3))

        wrapper_layout = QVBoxLayout(self.menu_wrapper)
        wrapper_layout.setContentsMargins(20, 20, 20, 20)

        # "card"
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
            background-color: #2b2b2b;
        }

        #menuCard {
            background-color: rgba(120, 110, 100, 180);
            border-radius: 20px;
        }

        QPushButton {
            background-color: #5a4f4a;
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
            background-color: #1e1e1e;
            border-radius: 10px;
        }
        """)

    # ===== API =====

    def add_menu_option(self, text, callback):
        btn = QPushButton(text)
        btn.clicked.connect(callback)
        self.menu_layout.addWidget(btn)

    def set_content(self, widget):
        # wyczyść
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
        self.add_menu_option("Wyjście", self.close)

        self.show_page("Witaj")

    def show_page(self, text):
        page = QWidget()
        layout = QVBoxLayout(page)

        label = QLabel(text)
        label.setStyleSheet("color: white; font-size: 24px;")
        label.setAlignment(Qt.AlignCenter)

        layout.addWidget(label)

        self.set_content(page)


# ===== START =====

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DemoApp()
    window.show()
    sys.exit(app.exec())
