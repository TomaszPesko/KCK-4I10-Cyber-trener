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
        # 1. Main navigation screen
        self.screen_main = MainScreen(self._handle_navigation)
        self.register_screen("main_page", self.screen_main)

        # 2. Create set module
        self.screen_create = CreateSetScreen(self._handle_navigation)
        self.register_screen("create_set", self.screen_create)

        # 3. Load set module
        self.screen_load = LoadSetScreen(self._handle_navigation)
        self.register_screen("load_set", self.screen_load)

        # 4. Progress analysis module
        self.screen_analyze = AnalyzeProgressScreen(
            self._handle_navigation,
            load_data_action_cb=lambda path: self._handle_db_load_request(path),
            get_db_connection_cb=lambda: self.db_module.get_connection(),
        )
        self.register_screen("analyze_progress", self.screen_analyze)

        # FIX: Safer signal registration without throwing noisy console RuntimeWarnings
        try:
            # We explicitly check if slots are registered before trying to sever them
            self.db_module.signals.data_loaded.disconnect(
                self.screen_analyze.handle_async_data_loaded
            )
        except (RuntimeError, TypeError):
            pass

        self.db_module.signals.data_loaded.connect(
            self.screen_analyze.handle_async_data_loaded
        )

        # 5. Manual set entry submodule
        self.screen_manual = ManualDefinitionScreen(
            self._handle_navigation, parent_widget=self
        )
        self.screen_manual.save_requested.connect(self._execute_manual_set_save)
        self.register_screen("manual_definition", self.screen_manual)

    def _execute_manual_set_save(self, workout_set):
        """Receives a completed WorkoutSet object and serializes it to a database path."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Workout Database Target", "", "SQLite Database (*.db)"
        )
        if not file_path:
            return

        self._ensure_db_thread_is_alive(file_path)
        self.db_module.request_set_save(workout_set)

        QMessageBox.information(
            self, "Success", f"Set saved successfully to target:\n{file_path}"
        )
        self.switch_to_screen("create_set")

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

    def _load_training_data_action(self, db_path=None):
        """Asynchronicznie ładuje dane serii z bazy danych do tabeli historii i cache.

        POPRAWKA: Dodano opcjonalny argument db_path, aby uniknąć ponownego
        otwierania okna wyboru pliku.
        """
        # 1. Jeśli ścieżka NIE została przekazana z zewnątrz, dopiero wtedy pytamy użytkownika
        if not db_path:
            from PySide6.QtWidgets import QFileDialog

            db_path, _ = QFileDialog.getOpenFileName(
                self,
                "Wybierz plik bazy danych z treningami",
                "",
                "Baza danych SQLite (*.db *.sqlite);;Wszystkie pliki (*)",
            )
            # Jeśli użytkownik zamknął okno bez wyboru pliku, przerywamy akcję
            if not db_path:
                print("[CyberTrener] Anulowano wybór bazy danych przy ładowaniu.")
                return

        print(f"[Database] Zażądano odczytu z bazy: {db_path}")

        # 2. Ustawiamy ścieżkę w module bazy danych i uruchamiamy wątek (jeśli nie żyje)
        self.db_module.db_path = db_path
        if not self.db_module.is_alive():
            print("Database module started in a separate thread...")
            self.db_module.start()

        # 3. Wysyłamy właściwe żądanie o pobranie danych z wątku
        # (Upewnij się, że ta metoda w Twoim db_module nazywa się dokładnie tak, np. request_all_data)
        self.db_module.request_all_data()

    def _handle_db_load_request(self, db_path):
        """Nowa metoda pośrednicząca, która konfiguruje db_module i bezpośrednio

        zleca asynchroniczny odczyt, OMIJAJĄC stare okno dialogowe.
        """
        try:
            # Ustawiamy plik bazy danych
            self.db_module.db_path = db_path

            # Jeśli wątek bazy jeszcze nie żyje, odpalamy go
            if not self.db_module.is_alive():
                self.db_module.start()

            # !!! KLUCZOWA POPRAWKA !!!
            # Zamiast odpalać samą funkcję self._load_training_data_action(),
            # która ma w środku zaszyte okno dialogowe, bezpośrednio wysyłamy
            # żądanie do publicznego API Twojego DatabaseModule:
            self.db_module.request_all_data()

            print(f"[Database] Zażądano asynchronicznego odczytu z bazy: {db_path}")

        except Exception as e:
            print(
                f"[CyberTrener] Błąd podczas przekazywania bazy danych do modułu: {e}"
            )


def main():
    app = QApplication(sys.argv)
    window = CyberTrener()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
