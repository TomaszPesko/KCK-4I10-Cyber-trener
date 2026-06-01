import sys
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from src.dataStorageModule.DataStorageModule import DatabaseModule
from src.include.set_data import WorkoutSet
from src.menuModule.date_dialog import DateTimeDialog
from src.menuModule.manual_set_widget import (
    DurationDialog,
    ManualPreviewWidget,
    RepetitionDialog,
    TrainingDataHistoryWidget,
)
from src.menuModule.menu import AppWindow, Screen


class CyberTrener(AppWindow):
    def __init__(self):
        self.db_module = DatabaseModule(db_path="cyber_trainer.db")

        # Temporary instance for manually building a set
        self.manual_set = WorkoutSet(location="", duration=0)
        self.manual_set.execution_date = (
            ""  # Enforce empty string for initial underscores
        )

        super().__init__(title="CyberTrener - Twój E-Trener AI")
        self._initialize_screens()
        self.switch_to_screen("main_page")

    def _initialize_screens(self):
        # ----------------------------------------------------
        # 1. MAIN PAGE
        # ----------------------------------------------------
        main_content = self._create_content_placeholder(
            "CyberTrener AI", "Witaj! Wybierz moduł z menu po lewej."
        )
        self.screen_main = Screen(main_content)
        self.screen_main.add_option(
            "Tworzenie serii", lambda: self.switch_to_screen("create_set")
        )
        self.screen_main.add_option(
            "Wczytywanie serii", lambda: self.switch_to_screen("load_set")
        )
        self.screen_main.add_option(
            "Analiza postępów", lambda: self.switch_to_screen("analyze_progress")
        )
        self.screen_main.add_option("Zamknij program", self.close)
        self.register_screen("main_page", self.screen_main)

        # ----------------------------------------------------
        # 2. MODULE: CREATE SET (Tworzenie serii)
        # ----------------------------------------------------
        create_content = self._create_content_placeholder(
            "Nowa Seria Treningowa", "Wybierz sposób zapisu lub perspektywę AI."
        )
        self.screen_create = Screen(create_content)
        self.screen_create.add_option("Start", self._start_recording_action)
        self.screen_create.add_option(
            "Perspektywa z przodu", lambda: self._set_perspective_action("Front")
        )
        self.screen_create.add_option(
            "Perspektywa z boku", lambda: self._set_perspective_action("Side")
        )
        self.screen_create.add_option(
            "Zdefiniuj Serię Ręcznie", self._enter_manual_mode_action
        )
        self.screen_create.add_option("Zapisz serię", self._save_set_action)
        self.screen_create.add_option(
            "Wróć", lambda: self.switch_to_screen("main_page")
        )
        self.register_screen("create_set", self.screen_create)

        # ----------------------------------------------------
        # 3. MODULE: LOAD SET (Wczytywanie serii)
        # ----------------------------------------------------
        load_content = self._create_content_placeholder(
            "Wczytywanie Serii", "Zarządzaj wczytanymi danymi treningowymi."
        )
        self.screen_load = Screen(load_content)
        self.screen_load.add_option(
            "Perspektywa z przodu",
            lambda: self._dummy_action("Wczytywanie: Perspektywa z przodu"),
        )
        self.screen_load.add_option(
            "Perspektywa z boku",
            lambda: self._dummy_action("Wczytywanie: Perspektywa z boku"),
        )
        self.screen_load.add_option("Zapisz serię", self._save_set_action)
        self.screen_load.add_option("Wróć", lambda: self.switch_to_screen("main_page"))
        self.register_screen("load_set", self.screen_load)

        # ----------------------------------------------------
        # 4. MODULE: ANALYZE PROGRESS (Analiza postępów)
        # ----------------------------------------------------
        # Zastępujemy zwykły placeholder naszym nowym zaawansowanym widgetem historycznym
        self.history_widget = TrainingDataHistoryWidget()

        # Tworzymy layout, w którym u góry będzie informacja o module, a pod nią tabela danych
        analyze_container = QWidget()
        analyze_layout = QVBoxLayout(analyze_container)
        analyze_layout.setContentsMargins(10, 10, 10, 10)

        lbl_info = QLabel("Centrum Statystyk i Historii Treningu")
        lbl_info.setStyleSheet(
            "color: #00cc66; font-size: 20px; font-weight: bold; margin-bottom: 5px;"
        )
        lbl_info.setAlignment(Qt.AlignCenter)

        analyze_layout.addWidget(lbl_info)
        analyze_layout.addWidget(
            self.history_widget
        )  # Dodanie drzewa serii na ekran główny analizy

        self.screen_analyze = Screen(analyze_container)
        self.screen_analyze.add_option(
            "Wczytaj dane treningowe", self._load_training_data_action
        )
        self.screen_analyze.add_option(
            "Jakość serii", lambda: self._dummy_action("Analiza: Jakość serii")
        )
        self.screen_analyze.add_option(
            "Ilość powtórzeń", lambda: self._dummy_action("Analiza: Ilość powtórzeń")
        )
        self.screen_analyze.add_option(
            "Czas trwania serii", lambda: self._dummy_action("Analiza: Czas trwania")
        )
        self.screen_analyze.add_option(
            "Liczba serii w ciągu dnia",
            lambda: self._dummy_action("Analiza: Liczba serii/dzień"),
        )
        self.screen_analyze.add_option(
            "Wróć", lambda: self.switch_to_screen("main_page")
        )
        self.register_screen("analyze_progress", self.screen_analyze)

        # CONNECT SIGNAL FROM DB TO UI WIDGET
        # To krytyczne miejsce: sygnał bezpiecznie przekaże dane między wątkami do metody rysującej drzewo
        self.db_module.signals.data_loaded.connect(self.history_widget.populate_data)

        # ----------------------------------------------------
        # SUBMODULE: MANUAL SET DEFINITION
        # ----------------------------------------------------
        self.manual_preview = ManualPreviewWidget()
        self.screen_manual = Screen(self.manual_preview)
        self.screen_manual.add_option("📍 Lokalizacja", self._set_manual_location)
        self.screen_manual.add_option("⏱ Czas trwania serii", self._set_manual_duration)
        self.screen_manual.add_option("📅 Data i godzina", self._set_manual_datetime)
        self.screen_manual.add_option(
            "＋ Dodaj powtórzenie", self._add_manual_repetition
        )
        self.screen_manual.add_option("💾 Zapisz do bazy", self._save_manual_to_db)
        self.screen_manual.add_option(
            "⬅ Wróć", lambda: self.switch_to_screen("create_set")
        )
        self.register_screen("manual_definition", self.screen_manual)

    # ===== CALLBACKS & LOGIC =====

    def _dummy_action(self, action_name: str):
        """Standard dummy callback for unimplemented features."""
        print(f"[UI] Kliknięto: {action_name}")
        # Można dodać powiadomienie w UI
        # QMessageBox.information(self, "Informacja", f"Wywołano: {action_name}")

    def _enter_manual_mode_action(self):
        self.manual_set = WorkoutSet(location="", duration=0)
        self.manual_set.execution_date = ""
        self._refresh_right_preview()
        self.switch_to_screen("manual_definition")

    def _refresh_right_preview(self):
        loc = self.manual_set.location if self.manual_set.location else "___"

        # Nowe formatowanie czasu na minuty i sekundy w podglądzie
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
            self,
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
            current_total_seconds=self.manual_set.duration_seconds, parent=self
        )
        if dialog.exec() == DurationDialog.Accepted:
            self.manual_set.duration_seconds = dialog.get_total_seconds()
            self._refresh_right_preview()

    def _set_manual_datetime(self):
        dialog = DateTimeDialog(parent=self)
        if dialog.exec() == DateTimeDialog.Accepted:
            self.manual_set.execution_date = dialog.get_date_string()
            self._refresh_right_preview()

    def _add_manual_repetition(self):
        dialog = RepetitionDialog(self)
        if dialog.exec() == RepetitionDialog.Accepted:
            self.manual_set.add_repetition(dialog.get_data())
            self._refresh_right_preview()

    def _save_manual_to_db(self):
        if not self.manual_set.repetitions:
            QMessageBox.warning(self, "Błąd", "Nie możesz zapisać serii bez powtórzeń!")
            return

        if not self.manual_set.location:
            self.manual_set.location = "Dom"
        if not self.manual_set.execution_date:
            self.manual_set.execution_date = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Zapisz bazę danych", "", "Baza danych (*.db)"
        )
        if not file_path:
            return

        self.db_module.db_path = file_path
        if not self.db_module.is_alive():
            try:
                self.db_module.start()
            except RuntimeError:
                pass

        self.db_module.request_set_save(self.manual_set)
        QMessageBox.information(self, "Sukces", f"Seria zapisana w:\n{file_path}")
        self.switch_to_screen("create_set")

    def _create_content_placeholder(self, title: str, subtitle: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
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
        return widget

    def _start_recording_action(self):
        print("[Camera] Starting stream...")

    def _set_perspective_action(self, p):
        print(f"[AI Model] Perspective: {p}")

    def _save_set_action(self):
        print("[Database] Auto-saving set...")

    def _load_training_data_action(self):
        """Prompts user to select a SQLite file, re-points the db_module and fires asynchronous data read."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz plik bazy danych SQLite do odczytu",
            "",
            "Baza danych (*.db);;Wszystkie pliki (*)",
        )
        if not file_path:
            return

        # Przełączenie ścieżki i upewnienie się, że wątek bazy działa
        self.db_module.db_path = file_path
        if not self.db_module.is_alive():
            try:
                self.db_module.start()
            except RuntimeError:
                pass  # Wątek mógł już być wystartowany wcześniej

        # Wyślij asynchroniczne żądanie odczytu danych do kolejki wątku bazy
        self.db_module.request_all_data()

        print(f"[Database] Zażądano odczytu z bazy: {file_path}")


def main():
    app = QApplication(sys.argv)
    window = CyberTrener()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
