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
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class Screen:
    """Klasa reprezentująca pojedynczy ekran aplikacji (Menu + Zawartość)."""

    def __init__(self, content_widget: QWidget):
        self.content_widget = content_widget
        self.options = []  # Lista krotek: (tekst_przycisku, funkcja_callback)

    def add_option(self, text: str, callback):
        """Dodaje opcję do lewego menu dla tego konkretnego ekranu."""
        self.options.append((text, callback))


class AppWindow(QWidget):
    """Główne okno-szablon działające jako silnik aplikacji z zablokowanym podziałem."""

    def __init__(self, title="Aplikacja", bg_image_path="gui_background.jpeg"):
        super().__init__()
        self.setWindowTitle(title)

        screen_geom = QApplication.primaryScreen().geometry()
        self.resize(int(screen_geom.width() * 0.8), int(screen_geom.height() * 0.8))
        self.setMinimumSize(900, 600)

        self._screens = {}  # Słownik identyfikatorów ekranów

        # ===== BACKGROUND =====
        self.bg_label = QLabel(self)
        self.bg_label.setScaledContents(True)
        if bg_image_path:
            self.bg_label.setPixmap(QPixmap(bg_image_path))

        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(20)
        self.bg_label.setGraphicsEffect(blur)

        # ===== ROOT CONTAINER =====
        self.main_container = QWidget(self)
        root_layout = QHBoxLayout(self.main_container)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # ===== HORIZONTAL LAYOUT (Zamiast Splittera) =====
        # Używamy zwykłego układu, dzięki czemu podział jest całkowicie zablokowany
        self.split_layout = QHBoxLayout()
        self.split_layout.setSpacing(10)  # Odstęp między menu a zawartością
        root_layout.addLayout(self.split_layout)

        # ======================
        # LEFT MENU (Stacked)
        # ======================
        self.menu_wrapper = QWidget()
        self.menu_wrapper.setMinimumWidth(220)
        self.menu_wrapper.setMaximumWidth(380)

        self.wrapper_layout = QVBoxLayout(self.menu_wrapper)

        # QStackedWidget dla paneli menu
        self.menu_stack = QStackedWidget()
        self.wrapper_layout.addWidget(self.menu_stack, alignment=Qt.AlignTop)

        # ======================
        # RIGHT CONTENT (Stacked)
        # ======================
        self.content_frame = QFrame()
        self.content_frame.setObjectName("contentArea")

        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(20, 20, 20, 20)

        # QStackedWidget dla zawartości prawostronnej
        self.content_stack = QStackedWidget()
        self.content_layout.addWidget(self.content_stack)

        # ===== DODANIE DO UKŁADU Z PROPORCJAMI =====
        # Proporcje 3:7 (Menu zajmuje 3 części, Treść zajmuje 7 części przestrzeni)
        self.split_layout.addWidget(self.menu_wrapper, stretch=3)
        self.split_layout.addWidget(self.content_frame, stretch=7)

        # ===== STYLESHEET =====
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

        # Aktualizacja marginesów we wszystkich wygenerowanych menu-cardach
        for i in range(self.menu_stack.count()):
            card = self.menu_stack.widget(i)
            if card and card.layout():
                card.layout().setContentsMargins(pad_w, pad_h, pad_w, pad_h)

        super().resizeEvent(event)

    # ===== PUBLIC API =====

    def register_screen(self, name: str, screen: Screen):
        """Rejestruje nowy ekran w aplikacji."""
        menu_card = QFrame()
        menu_card.setObjectName("menuCard")
        menu_card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        card_layout = QVBoxLayout(menu_card)
        card_layout.setSpacing(8)

        for text, callback in screen.options:
            btn = QPushButton(text)
            btn.clicked.connect(callback)
            card_layout.addWidget(btn)

        self.menu_stack.addWidget(menu_card)
        self.content_stack.addWidget(screen.content_widget)

        # Zapamiętujemy indeks powiązany z nazwą ekranu
        self._screens[name] = self.menu_stack.count() - 1

    def switch_to_screen(self, name: str):
        """Zmienia aktualnie wyświetlany ekran."""
        if name in self._screens:
            idx = self._screens[name]
            self.menu_stack.setCurrentIndex(idx)
            self.content_stack.setCurrentIndex(idx)
        else:
            print(f"Błąd: Ekran o nazwie '{name}' nie istnieje.")

    def refresh_screen_menu(self, name: str, screen: Screen):
        """Usuwa stare przyciski z menu_card danego ekranu i generuje je na nowo."""
        if name in self._screens:
            idx = self._screens[name]
            menu_card = self.menu_stack.widget(idx)

            # Czyszczenie starego layoutu z przycisków
            if menu_card and menu_card.layout():
                layout = menu_card.layout()
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()

                # Dodanie nowych przycisków na podstawie zmodyfikowanej listy options
                for text, callback in screen.options:
                    btn = QPushButton(text)
                    btn.clicked.connect(callback)
                    layout.addWidget(btn)


# ===== PRZYKŁAD UŻYCIA (DEMO) =====


def create_dummy_page(text, color="#00cc66"):
    page = QWidget()
    layout = QVBoxLayout(page)
    label = QLabel(text)
    label.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold;")
    label.setAlignment(Qt.AlignCenter)
    layout.addWidget(label)
    return page
