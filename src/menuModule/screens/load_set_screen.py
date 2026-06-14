import os

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QInputDialog,
    QLineEdit,
    QMessageBox,
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


class LoadSetScreen(Screen):
    def __init__(self, navigator_cb):
        self.main_container = QWidget()
        main_layout = QVBoxLayout(self.main_container)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.workout_set = WorkoutSet(location="None", duration=0)

        self.display_stack = QStackedWidget()
        main_layout.addWidget(self.display_stack)

        self.history_preview_widget = TrainingDataHistoryWidget()
        self.display_stack.addWidget(self.history_preview_widget)

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
        self.options.clear()
        front_txt = f"📸 Front: {self._get_filename_or_empty(self.front_video_path)}"
        self.add_option(front_txt, self._select_front_video)

        side_txt = f"📸 Side: {self._get_filename_or_empty(self.side_video_path)}"
        self.add_option(side_txt, self._select_side_video)

        self.add_option(f"📍 Location: {self.workout_set.location}", self._set_location)
        self.add_option(
            f"📅 Timestamp: {self.workout_set.execution_date[:16]}", self._set_datetime
        )

        self.add_option("📊 Show Statistics (Tree)", self._show_static_stats)
        self.add_option("⚙️ Run AR Analysis View", self._start_video_analysis)
        self.add_option("💾 Save Set to Database", self._save_set_to_database)
        self.add_option("⬅️ Back", self._on_back_clicked)

    def _get_filename_or_empty(self, path):
        return os.path.basename(path) if path else "--- SELECT ---"

    def _select_front_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_container,
            "Select Front Perspective Recording",
            "",
            "Video Files (*.mp4 *.avi *.mov)",
        )
        if file_path:
            self.front_video_path = file_path
            self._trigger_background_pre_extraction()

    def _select_side_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_container,
            "Select Side Perspective Recording",
            "",
            "Video Files (*.mp4 *.avi *.mov)",
        )
        if file_path:
            self.side_video_path = file_path
            self._trigger_background_pre_extraction()

    def _trigger_background_pre_extraction(self):
        if not self.front_video_path and not self.side_video_path:
            return

        extracted_reps = run_fast_background_analysis(
            self.front_video_path, self.side_video_path
        )

        self.workout_set.repetitions.clear()
        for rep_tuple in extracted_reps:
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

        self.workout_set.duration_seconds = len(extracted_reps) * 2
        self._refresh_history_tree()
        self._update_menu_and_refresh()

    def _set_location(self):
        text, ok = QInputDialog.getText(
            self.main_container,
            "Modify Workout Session",
            "Enter location label:",
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

    def _update_menu_and_refresh(self):
        self._build_menu()
        window = self.main_container.window()
        if window and hasattr(window, "refresh_screen_menu"):
            window.refresh_screen_menu("load_set", self)

    def _show_static_stats(self):
        self.display_stack.setCurrentIndex(0)

    def _start_video_analysis(self):
        if not self.front_video_path and not self.side_video_path:
            QMessageBox.warning(
                self.main_container,
                "Missing Data Source",
                "Please bind at least one pipeline tracking target!",
            )
            return

        self.display_stack.setCurrentIndex(1)
        self.video_display.set_modes(
            bool(self.front_video_path), bool(self.side_video_path)
        )
        self._toggle_menu_buttons(enabled=False)

        self.analysis_thread = VideoAnalysisThread(
            self.front_video_path, self.side_video_path
        )
        self.analysis_thread.frame_processed.connect(self.video_display.update_frames)
        self.analysis_thread.finished_analysis.connect(self._on_analysis_finished)
        self.analysis_thread.start()

    def _on_analysis_finished(self, final_stats):
        self._toggle_menu_buttons(enabled=True)
        self.display_stack.setCurrentIndex(0)
        self._trigger_background_pre_extraction()

    def _save_set_to_database(self):
        if not self.front_video_path and not self.side_video_path:
            QMessageBox.critical(
                self.main_container,
                "Serialization Halt",
                "Cannot execute storage queries on unverified tracking source targets.",
            )
            return

        db_path, _ = QFileDialog.getSaveFileName(
            self.main_container,
            "Select Destination Database File",
            "",
            "Database Files (*.db *.sqlite);;All Files (*)",
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
                self.main_container,
                "Transaction Dispatched",
                f"Workout transaction successfully committed to target database file:\n{db_path}",
            )
            self._on_back_clicked()

    def _toggle_menu_buttons(self, enabled: bool):
        window = self.main_container.window()
        if window and hasattr(window, "menu_stack"):
            active_menu_card = window.menu_stack.currentWidget()
            if active_menu_card:
                for btn in active_menu_card.findChildren(QPushButton):
                    if "Back" not in btn.text():
                        btn.setEnabled(enabled)

    def _on_back_clicked(self):
        if self.analysis_thread and self.analysis_thread.isRunning():
            self.analysis_thread.stop()
        self.front_video_path = None
        self.side_video_path = None
        self.workout_set = WorkoutSet(location="None", duration=0)
        self._refresh_history_tree()
        self.display_stack.setCurrentIndex(0)
        self._update_menu_and_refresh()
        self.navigator_cb("main_page")
