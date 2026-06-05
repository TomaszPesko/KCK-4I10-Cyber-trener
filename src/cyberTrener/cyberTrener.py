import sys

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from src.dataStorageModule.DataStorageModule import DatabaseModule
from src.menuModule.menu import AppWindow

# Import nowo wydzielonych ekranów
from src.menuModule.screens import (
    AnalyzeProgressScreen,
    CreateSetScreen,
    LoadSetScreen,
    MainScreen,
    ManualDefinitionScreen,
)


class CyberTrener(AppWindow):
    def __init__(self):
        self.db_module = DatabaseModule(db_path="cyber_trainer.db")
        super().__init__(title="CyberTrener - Twój E-Trener AI")

        self._initialize_screens()
        self.switch_to_screen("main_page")

    def _initialize_screens(self):
        # 1. Główny ekran nawigacji
        self.screen_main = MainScreen(self._handle_navigation)
        self.register_screen("main_page", self.screen_main)

        # 2. Moduł: Tworzenie serii
        self.screen_create = CreateSetScreen(self._handle_navigation)
        self.register_screen("create_set", self.screen_create)

        # 3. Moduł: Wczytywanie serii
        self.screen_load = LoadSetScreen(self._handle_navigation)
        self.register_screen("load_set", self.screen_load)

        # 4. Moduł: Analiza postępów
        self.screen_analyze = AnalyzeProgressScreen(
            self._handle_navigation, self._load_training_data_action
        )
        self.register_screen("analyze_progress", self.screen_analyze)

        # Połączenie sygnału bazy danych bezpośrednio z widgetem wewnątrz odizolowanego ekranu
        self.db_module.signals.data_loaded.connect(
            self.screen_analyze.history_widget.populate_data
        )

        # 5. Podmoduł: Ręczne definiowanie serii
        self.screen_manual = ManualDefinitionScreen(
            self._handle_navigation, parent_widget=self
        )
        self.screen_manual.save_requested.connect(self._execute_manual_set_save)
        self.register_screen("manual_definition", self.screen_manual)

    def _handle_navigation(self, screen_name: str):
        """Centralny punkt zarządzania przełączaniem ekranów."""
        if screen_name == "close":
            self.close()
        elif screen_name == "manual_definition":
            self.screen_manual.reset_set()
            self.switch_to_screen(screen_name)
        else:
            self.switch_to_screen(screen_name)

    def _ensure_db_thread_is_alive(self, file_path: str):
        """Pomocnicza metoda dbająca o prawidłowy stan wątku SQLite."""
        self.db_module.db_path = file_path
        if not self.db_module.is_alive():
            try:
                self.db_module.start()
            except RuntimeError:
                pass

    def _execute_manual_set_save(self, workout_set):
        """Odbiera przygotowany obiekt serii i zapisuje go przy użyciu bazy danych."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Zapisz bazę danych", "", "Baza danych (*.db)"
        )
        if not file_path:
            return

        self._ensure_db_thread_is_alive(file_path)
        self.db_module.request_set_save(workout_set)

        QMessageBox.information(self, "Sukces", f"Seria zapisana w:\n{file_path}")
        self.switch_to_screen("create_set")

    def _load_training_data_action(self):
        """Obsługa asynchronicznego żądania odczytu danych z pliku DB."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz plik bazy danych SQLite do odczytu",
            "",
            "Baza danych (*.db);;Wszystkie pliki (*)",
        )
        if not file_path:
            return

        self._ensure_db_thread_is_alive(file_path)
        self.db_module.request_all_data()
        print(f"[Database] Zażądano odczytu z bazy: {file_path}")


def main():
    app = QApplication(sys.argv)
    window = CyberTrener()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
