from datetime import datetime
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QFileDialog,
)
from src.menuModule.menu import Screen
from src.include.set_data import WorkoutSet
from src.menuModule.date_dialog import DateTimeDialog
from src.menuModule.manual_set_widget import (
    DurationDialog,
    ManualPreviewWidget,
    RepetitionDialog,
    TrainingDataHistoryWidget,
)


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


class MainScreen(BaseScreen):
    def __init__(self, navigator_cb):
        super().__init__("CyberTrener AI", "Witaj! Wybierz moduł z menu po lewej.")
        self.add_option("Tworzenie serii", lambda: navigator_cb("create_set"))
        self.add_option("Wczytywanie serii", lambda: navigator_cb("load_set"))
        self.add_option("Analiza postępów", lambda: navigator_cb("analyze_progress"))
        self.add_option("Zamknij program", lambda: navigator_cb("close"))


class CreateSetScreen(BaseScreen):
    def __init__(self, navigator_cb):
        super().__init__(
            "Nowa Seria Treningowa", "Wybierz sposób zapisu lub perspektywę AI."
        )
        self.add_option("Start", lambda: print("[Camera] Starting stream..."))
        self.add_option(
            "Perspektywa z przodu", lambda: print("[AI Model] Perspective: Front")
        )
        self.add_option(
            "Perspektywa z boku", lambda: print("[AI Model] Perspective: Side")
        )
        self.add_option(
            "Zdefiniuj Serię Ręcznie", lambda: navigator_cb("manual_definition")
        )
        self.add_option("Zapisz serię", lambda: print("[Database] Auto-saving set..."))
        self.add_option("Wróć", lambda: navigator_cb("main_page"))


class LoadSetScreen(BaseScreen):
    def __init__(self, navigator_cb):
        super().__init__(
            "Wczytywanie Serii", "Zarządzaj wczytanymi danymi treningowymi."
        )
        self.add_option(
            "Perspektywa z przodu",
            lambda: print("[UI] Kliknięto: Wczytywanie: Perspektywa z przodu"),
        )
        self.add_option(
            "Perspektywa z boku",
            lambda: print("[UI] Kliknięto: Wczytywanie: Perspektywa z boku"),
        )
        self.add_option("Zapisz serię", lambda: print("[Database] Auto-saving set..."))
        self.add_option("Wróć", lambda: navigator_cb("main_page"))


class AnalyzeProgressScreen(Screen):
    def __init__(self, navigator_cb, load_data_cb):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)

        lbl_info = QLabel("Centrum Statystyk i Historii Treningu")
        lbl_info.setStyleSheet(
            "color: #00cc66; font-size: 20px; font-weight: bold; margin-bottom: 5px;"
        )
        lbl_info.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_info)

        self.history_widget = TrainingDataHistoryWidget()
        layout.addWidget(self.history_widget)

        super().__init__(container)
        self.add_option("Wczytaj dane treningowe", load_data_cb)
        self.add_option(
            "Jakość serii", lambda: print("[UI] Kliknięto: Analiza: Jakość serii")
        )
        self.add_option(
            "Ilość powtórzeń", lambda: print("[UI] Kliknięto: Analiza: Ilość powtórzeń")
        )
        self.add_option(
            "Czas trwania serii", lambda: print("[UI] Kliknięto: Analiza: Czas trwania")
        )
        self.add_option(
            "Liczba serii w ciągu dnia",
            lambda: print("[UI] Kliknięto: Analiza: Liczba serii/dzień"),
        )
        self.add_option("Wróć", lambda: navigator_cb("main_page"))


class ManualDefinitionScreen(Screen, QObject):
    # Sygnał wysyłany do głównej klasy w celu zapisania skonstruowanej serii
    save_requested = Signal(object)

    def __init__(self, navigator_cb, parent_widget):
        # QObject.__init__(self) musi być jawne przy wielodziedziczeniu w PySide
        QObject.__init__(self)
        self.parent_widget = parent_widget
        self.navigator_cb = navigator_cb

        self.manual_set = WorkoutSet(location="", duration=0)
        self.manual_set.execution_date = ""

        self.manual_preview = ManualPreviewWidget()
        super().__init__(self.manual_preview)

        self.add_option("📍 Lokalizacja", self._set_manual_location)
        self.add_option("⏱ Czas trwania serii", self._set_manual_duration)
        self.add_option("📅 Data i godzina", self._set_manual_datetime)
        self.add_option("＋ Dodaj powtórzenie", self._add_manual_repetition)
        self.add_option("💾 Zapisz do bazy", self._save_manual_to_db)
        self.add_option("⬅ Wróć", lambda: self.navigator_cb("create_set"))

        self._refresh_right_preview()

    def reset_set(self):
        self.manual_set = WorkoutSet(location="", duration=0)
        self.manual_set.execution_date = ""
        self._refresh_right_preview()

    def _refresh_right_preview(self):
        loc = self.manual_set.location if self.manual_set.location else "___"
        if self.manual_set.duration_seconds > 0:
            m = self.manual_set.duration_seconds // 60
            s = self.manual_set.duration_seconds % 60
            dur = f"{m}m {s}s" if m > 0 else f"{s} s"
        else:
            dur = "___"
        date = (
            self.manual_set.execution_date if self.manual_set.execution_date else "___"
        )
        self.manual_preview.update_view(loc, dur, date, self.manual_set.repetitions)

    def _set_manual_location(self):
        text, ok = QInputDialog.getText(
            self.parent_widget,
            "Lokalizacja",
            "Wpisz miejsce:",
            QLineEdit.Normal,
            self.manual_set.location,
        )
        if ok:
            self.manual_set.location = text.strip()
            self._refresh_right_preview()

    def _set_manual_duration(self):
        dialog = DurationDialog(
            current_total_seconds=self.manual_set.duration_seconds,
            parent=self.parent_widget,
        )
        if dialog.exec() == DurationDialog.Accepted:
            self.manual_set.duration_seconds = dialog.get_total_seconds()
            self._refresh_right_preview()

    def _set_manual_datetime(self):
        dialog = DateTimeDialog(parent=self.parent_widget)
        if dialog.exec() == DateTimeDialog.Accepted:
            self.manual_set.execution_date = dialog.get_date_string()
            self._refresh_right_preview()

    def _add_manual_repetition(self):
        dialog = RepetitionDialog(self.parent_widget)
        if dialog.exec() == RepetitionDialog.Accepted:
            self.manual_set.add_repetition(dialog.get_data())
            self._refresh_right_preview()

    def _save_manual_to_db(self):
        if not self.manual_set.repetitions:
            QMessageBox.warning(
                self.parent_widget, "Błąd", "Nie możesz zapisać serii bez powtórzeń!"
            )
            return

        if not self.manual_set.location:
            self.manual_set.location = "Dom"
        if not self.manual_set.execution_date:
            self.manual_set.execution_date = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        # Emitujemy obiekt serii do głównej klasy, która zajmie się plikami i bazą danych
        self.save_requested.emit(self.manual_set)
