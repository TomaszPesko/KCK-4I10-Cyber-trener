# ==> ./menuModule/screens/load_set_screen.py <==
import os

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.include.set_data import Repetition, WorkoutSet
from src.menuModule.menu import Screen
from src.menuModule.widgets.date_dialog import DateTimeDialog
from src.menuModule.widgets.training_data_history_widget import (
    TrainingDataHistoryWidget,
)
from src.menuModule.widgets.video_player import (
    VideoAnalysisThread,
    VideoDisplayWidget,
    run_fast_background_analysis,
)
from src.menuModule.widgets.video_sync_widget import VideoSyncWidget


class LoadSetScreen(Screen):
    def __init__(self, navigator_cb):
        self.main_container = QWidget()
        main_layout = QVBoxLayout(self.main_container)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.workout_set = WorkoutSet(location="None", duration=0)

        # Stos widoków po prawej stronie
        self.display_stack = QStackedWidget()
        main_layout.addWidget(self.display_stack)

        # Indeks 0: Widżet synchronizacji (Domyślny widok startowy)
        self.sync_widget = VideoSyncWidget()
        self.display_stack.addWidget(self.sync_widget)

        # Indeks 1: Drzewo historii (Wywoływane po analizie / Pokaż statystyki)
        self.history_preview_widget = TrainingDataHistoryWidget()
        self.display_stack.addWidget(self.history_preview_widget)

        # Indeks 2: Odtwarzacz AR
        self.video_display = VideoDisplayWidget()
        self.display_stack.addWidget(self.video_display)

        super().__init__(self.main_container)
        self.navigator_cb = navigator_cb

        self.front_video_path = None
        self.side_video_path = None
        self.analysis_thread = None

        self._build_menu()
        self._refresh_history_tree()

    def _build_menu(self):
        """Buduje menu boczne w języku polskim z zachowaniem pierwotnego układu."""
        self.options.clear()

        front_txt = f"📸 Przód: {self._get_filename_or_empty(self.front_video_path)}"
        self.add_option(front_txt, self._select_front_video)

        side_txt = f"📸 Bok: {self._get_filename_or_empty(self.side_video_path)}"
        self.add_option(side_txt, self._select_side_video)

        self.add_option(
            f"📍 Lokalizacja: {self.workout_set.location}", self._set_location
        )
        self.add_option(
            f"📅 Data i godzina: {self.workout_set.execution_date[:16]}",
            self._set_datetime,
        )

        # Kluczowy przycisk przetwarzania żądany w architekturze
        self.add_option("⚙️ Analizuj", self._execute_analysis_processing)

        self.add_option("📊 Pokaż statystyki (Drzewo)", self._show_static_stats)
        self.add_option("👁️ Uruchom podgląd AR", self._start_video_analysis)
        self.add_option("💾 Zapisz serię do bazy", self._save_set_to_database)
        self.add_option("⬅️ Wróć", self._on_back_clicked)

    def _get_filename_or_empty(self, path):
        return os.path.basename(path) if path else "--- WYBIERZ ---"

    def _select_front_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self.main_container,
            "Wybierz nagranie z przodu",
            "",
            "Wideo (*.mp4 *.avi *.mov)",
        )
        if path:
            self.front_video_path = path
            self.display_stack.setCurrentIndex(0)  # Powrót do widoku suwaków
            self.sync_widget.load_videos(self.front_video_path, self.side_video_path)
            self._update_menu_and_refresh()

    def _select_side_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self.main_container,
            "Wybierz nagranie z boku",
            "",
            "Wideo (*.mp4 *.avi *.mov)",
        )
        if path:
            self.side_video_path = path
            self.display_stack.setCurrentIndex(0)
            self.sync_widget.load_videos(self.front_video_path, self.side_video_path)
            self._update_menu_and_refresh()

    def _execute_analysis_processing(self):
        """Wykonuje cichą, błyskawiczną analizę wyciętego materiału i od razu ładuje drzewo wyników."""
        if not self.front_video_path and not self.side_video_path:
            QMessageBox.warning(
                self.main_container,
                "Brak danych",
                "Załaduj pliki wideo przed uruchomieniem analizy!",
            )
            return

        # 1. Pobieramy i ZAPAMIĘTUJEMY aktualne ramy wyznaczone przez użytkownika
        f_start, f_end, s_start, s_end = self.sync_widget.get_bounds()

        # Zwalniamy pliki w widżecie synchronizacji, aby funkcja analizy miała do nich dostęp
        self.sync_widget._release_caps()

        # 2. Uruchamiamy szybkie przetwarzanie w tle w ramach wyznaczonych suwakami
        results = run_fast_background_analysis(
            self.front_video_path, self.side_video_path, f_start, f_end, s_start, s_end
        )

        self.workout_set.repetitions.clear()
        for rep_tuple in results["reps"]:
            rep_obj = Repetition(
                speed=rep_tuple[0],
                quality=rep_tuple[1],
                shallow=bool(rep_tuple[2]),
                far=bool(rep_tuple[3]),
                tempo=bool(rep_tuple[4]),
            )
            rep_obj.error_too_shallow = bool(rep_tuple[2])
            rep_obj.error_too_far_from_chair = bool(rep_tuple[3])
            rep_obj.error_lacks_tempo_control = bool(rep_tuple[4])
            self.workout_set.add_repetition(rep_obj)

        self.workout_set.duration_seconds = len(results["reps"]) * 2
        self._refresh_history_tree()

        # Przełączenie widoku na drzewo statystyk
        self.display_stack.setCurrentWidget(self.history_preview_widget)

        if results["mismatch"]:
            QMessageBox.critical(
                self.main_container,
                "Niespójne dane",
                "Wykryto drastyczne rozbieżności ruchu! Sprawdź czy pliki są prawidłowe.",
            )

        # 3. POPRAWKA: Ponownie ładujemy wideo do widżetu synchronizacji, ale wymuszamy zachowanie starych pozycji suwaków!
        self.sync_widget.load_videos(self.front_video_path, self.side_video_path)
        self.sync_widget.restore_bounds(f_start, f_end, s_start, s_end)

    def _show_static_stats(self):
        self.display_stack.setCurrentWidget(self.history_preview_widget)

    def _start_video_analysis(self):
        """Uruchamia dynamiczne odtwarzanie klatek AR."""
        if not self.front_video_path and not self.side_video_path:
            return

        f_start, f_end, s_start, s_end = self.sync_widget.get_bounds()
        self.sync_widget._release_caps()

        self.display_stack.setCurrentWidget(self.video_display)
        self.video_display.set_modes(
            bool(self.front_video_path), bool(self.side_video_path)
        )
        self._toggle_menu_buttons(enabled=False)

        self.analysis_thread = VideoAnalysisThread(
            self.front_video_path, self.side_video_path, f_start, f_end, s_start, s_end
        )
        self.analysis_thread.frame_processed.connect(self.video_display.update_frames)
        self.analysis_thread.finished_analysis.connect(self._on_ar_playback_finished)
        self.analysis_thread.start()

    def _on_ar_playback_finished(self, final_stats):
        self._toggle_menu_buttons(enabled=True)
        self._execute_analysis_processing()

    def _set_location(self):
        text, ok = QInputDialog.getText(
            self.main_container,
            "Modyfikacja serii",
            "Wpisz lokalizację treningu:",
            QLineEdit.Normal,
            self.workout_set.location,
        )
        if ok:
            self.workout_set.location = text.strip() if text.strip() else "None"
            self._refresh_history_tree()
            self._update_menu_and_refresh()

    def _set_datetime(self):
        dialog = DateTimeDialog(parent=self.main_container)
        if dialog.exec() == QDialog.Accepted:
            self.workout_set.execution_date = dialog.get_date_string()
            self._refresh_history_tree()
            self._update_menu_and_refresh()

    def _refresh_history_tree(self):
        total, correct, faulty = self.workout_set.summarize_set()
        mapped_reps = []
        for r in self.workout_set.repetitions:
            mapped_reps.append(
                (
                    None,
                    None,
                    r.execution_speed_seconds,
                    r.quality_status,
                    1 if getattr(r, "error_too_shallow", False) else 0,
                    1 if getattr(r, "error_too_far_from_chair", False) else 0,
                    1 if getattr(r, "error_lacks_tempo_control", False) else 0,
                )
            )
        cache_contract = {
            "metadata": {
                "date": self.workout_set.execution_date,
                "location": self.workout_set.location,
                "duration": self.workout_set.duration_seconds,
                "total": total,
                "correct": correct,
                "faulty": faulty,
            },
            "repetitions": mapped_reps,
        }
        self.history_preview_widget.populate_data([cache_contract])

    def _save_set_to_database(self):
        if not self.workout_set.repetitions:
            QMessageBox.critical(
                self.main_container,
                "Zapis przerwany",
                "Nie można zapisać pustej serii. Wykonaj najpierw 'Analizuj'.",
            )
            return

        db_path, _ = QFileDialog.getSaveFileName(
            self.main_container,
            "Wybierz plik bazy danych",
            "",
            "Bazy danych (*.db *.sqlite)",
        )
        if not db_path:
            return

        window = self.main_container.window()
        if window and hasattr(window, "db_module"):
            window.db_module.db_path = db_path
            if hasattr(window, "_ensure_db_thread_is_alive"):
                window._ensure_db_thread_is_alive(db_path)
            window.db_module.request_set_save(self.workout_set)
            QMessageBox.information(
                self.main_container, "Sukces", "Seria zapisana pomyślnie."
            )
            self._on_back_clicked()

    def _toggle_menu_buttons(self, enabled: bool):
        window = self.main_container.window()
        if window and hasattr(window, "menu_stack"):
            active_card = window.menu_stack.currentWidget()
            if active_card:
                for btn in active_card.findChildren(QPushButton):
                    if "Wróć" not in btn.text():
                        btn.setEnabled(enabled)

    def _update_menu_and_refresh(self):
        self._build_menu()
        window = self.main_container.window()
        if window and hasattr(window, "refresh_screen_menu"):
            window.refresh_screen_menu("load_set", self)

    def _on_back_clicked(self):
        if self.analysis_thread and self.analysis_thread.isRunning():
            self.analysis_thread.stop()
        self.sync_widget._release_caps()
        self.front_video_path = None
        self.side_video_path = None
        self.workout_set = WorkoutSet(location="None", duration=0)
        self._refresh_history_tree()
        self.display_stack.setCurrentIndex(0)
        self._update_menu_and_refresh()
        self.navigator_cb("main_page")

    def restore_bounds(self, f_start, f_end, s_start, s_end):
        """Przywraca i blokuje suwaki na pozycjach wybranych przed uruchomieniem procesora analizy."""
        if self.front_cap:
            # Blokada bezpieczeństwa przed wyjściem poza zakres pliku
            self.slider_front_start.setValue(min(f_start, self.front_total_frames - 2))
            self.slider_front_end.setValue(min(f_end, self.front_total_frames - 1))
            self._update_front_preview(f_start)

        if self.side_cap:
            self.slider_side_start.setValue(min(s_start, self.side_total_frames - 2))
            self.slider_side_end.setValue(min(s_end, self.side_total_frames - 1))
            self._update_side_preview(s_start)
