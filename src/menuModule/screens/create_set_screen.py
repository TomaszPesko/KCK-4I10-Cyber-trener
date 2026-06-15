import os

import cv2 as cv
from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.dataStorageModule.DataStorageModule import DatabaseModule
from src.include.set_data import WorkoutSet
from src.menuModule.menu import Screen
from src.menuModule.widgets.camera_live_thread import CameraLiveThread
from src.menuModule.widgets.camera_preview_thread import CameraPreviewThread
from src.menuModule.widgets.date_dialog import DateTimeDialog
from src.menuModule.widgets.training_data_history_widget import (
    TrainingDataHistoryWidget,
)
from src.menuModule.widgets.video_player import VideoDisplayWidget
from src.videoAnalysisModule.VideoAnalyzer import VideoAnalyzer


class CreateSetScreen(Screen):
    def __init__(self, navigator_cb):
        self.main_container = QWidget()
        main_layout = QVBoxLayout(self.main_container)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.analyzer = VideoAnalyzer()
        self.db_module = DatabaseModule()
        self.db_module.start()

        self.navigator_cb = navigator_cb
        self.live_thread = None
        self.preview_thread = None
        self.compiled_live_set = None
        self.workout_set = WorkoutSet(location="Siłownia", duration=45)

        camera_options = ["Brak"] + [f"Kamera {i}" for i in range(10)]
        setup_panel = QHBoxLayout()

        setup_panel.addWidget(QLabel("Kamera przód:"))
        self.combo_front = QComboBox()
        self.combo_front.addItems(camera_options)
        self.combo_front.setCurrentIndex(0)
        self.combo_front.currentIndexChanged.connect(self._restart_passive_preview)
        setup_panel.addWidget(self.combo_front)

        setup_panel.addWidget(QLabel("Kamera bok:"))
        self.combo_side = QComboBox()
        self.combo_side.addItems(camera_options)
        self.combo_side.setCurrentIndex(0)
        self.combo_side.currentIndexChanged.connect(self._restart_passive_preview)
        setup_panel.addWidget(self.combo_side)

        main_layout.addLayout(setup_panel)

        self.lbl_coach_status = QLabel(
            "Wybierz źródło wideo z list powyżej, aby uruchomić podgląd kamer."
        )
        self.lbl_coach_status.setStyleSheet(
            "color: #ffcc00; font-size: 14px; font-weight: bold; margin-top: 5px; margin-bottom: 5px;"
        )
        self.lbl_coach_status.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.lbl_coach_status)

        self.display_stack = QStackedWidget()
        main_layout.addWidget(self.display_stack)

        self.video_display = VideoDisplayWidget()
        self.display_stack.addWidget(self.video_display)

        self.history_preview_widget = TrainingDataHistoryWidget()
        self.display_stack.addWidget(self.history_preview_widget)

        self.display_stack.setFixedHeight(380)
        self.display_stack.setCurrentIndex(0)

        super().__init__(self.main_container)
        self._build_menu()

    def _build_menu(self):
        self.options.clear()
        self.add_option("▶️ Uruchom Trenera AI", self._start_live_workout)
        self.add_option("🛑 Zatrzymaj Analizę", self._stop_live_workout)
        self.add_option(
            f"📍 Lokalizacja: {self.workout_set.location}", self._set_location
        )
        self.add_option(
            f"📅 Data i godzina: {self.workout_set.execution_date[:16]}",
            self._set_datetime,
        )
        self.add_option("💾 Zapisz serię do bazy", self._save_set_to_database)
        self.add_option(
            "✍️ Zdefiniuj serię ręcznie", lambda: self.navigator_cb("manual_definition")
        )
        self.add_option("⬅️ Wróć do menu", self._on_back_clicked)

    def _get_selected_camera_index(self, combo_box: QComboBox) -> int:
        text = combo_box.currentText()
        if text == "Brak":
            return -1
        return int(text.split(" ")[1])

    def _set_location(self):
        text, ok = QInputDialog.getText(
            self.main_container,
            "Modyfikacja serii",
            "Wpisz lokalizację treningu na żywo:",
            QLineEdit.Normal,
            self.workout_set.location,
        )
        if ok:
            self.workout_set.location = text.strip() if text.strip() else "Siłownia"
            self._build_menu()

    def _set_datetime(self):
        dialog = DateTimeDialog(parent=self.main_container)
        if dialog.exec() == QDialog.Accepted:
            self.workout_set.execution_date = dialog.get_date_string()
            self._build_menu()

    def _restart_passive_preview(self):
        if self.live_thread and self.live_thread.isRunning():
            return

        if self.preview_thread and self.preview_thread.isRunning():
            self.preview_thread.stop()
            self.preview_thread = None

        front_idx = self._get_selected_camera_index(self.combo_front)
        side_idx = self._get_selected_camera_index(self.combo_side)

        has_front = front_idx != -1
        has_side = side_idx != -1

        self.video_display.set_modes(has_front, has_side)

        if not has_front and not has_side:
            self.video_display.clear_views()
            return

        self.preview_thread = CameraPreviewThread(
            front_idx,
            side_idx,
            has_front,
            has_side,
        )
        self.preview_thread.frame_processed.connect(self.video_display.update_frames)
        self.preview_thread.start()

    def _start_live_workout(self):
        if self.live_thread and self.live_thread.isRunning():
            return

        if self.preview_thread and self.preview_thread.isRunning():
            self.preview_thread.stop()

        front_idx = self._get_selected_camera_index(self.combo_front)
        side_idx = self._get_selected_camera_index(self.combo_side)

        has_front = front_idx != -1
        has_side = side_idx != -1

        if not has_front and not has_side:
            QMessageBox.critical(
                self.main_container,
                "Błąd",
                "Wybierz przynajmniej jedną działającą kamerę.",
            )
            self._restart_passive_preview()
            return

        self.video_display.set_modes(has_front, has_side)
        self.display_stack.setCurrentIndex(0)
        self._toggle_menu_buttons(enabled=False)
        self.compiled_live_set = None

        self.live_thread = CameraLiveThread(
            self.analyzer, front_idx, side_idx, has_front, has_side
        )
        self.live_thread.frame_processed.connect(self.video_display.update_frames)
        self.live_thread.status_msg_updated.connect(self.lbl_coach_status.setText)
        self.live_thread.start()

    def _stop_live_workout(self):
        if self.live_thread and self.live_thread.isRunning():
            self.live_thread.stop()
            self.live_thread.wait()

            self.compiled_live_set = self.analyzer.compile_and_cache_workout_set(
                front_path="Live_Cam", side_path="Live_Cam", bounds_tuple=(0, 0, 0, 0)
            )

            if (
                not self.compiled_live_set
                or len(self.compiled_live_set.repetitions) == 0
            ):
                self.compiled_live_set = None
                self.display_stack.setCurrentIndex(0)
                self.lbl_coach_status.setStyleSheet(
                    "color: #ffcc00; font-weight: bold;"
                )
                self.lbl_coach_status.setText(
                    "Analiza przerwana przez użytkownika przed synchronizacją."
                )
            else:
                self.compiled_live_set.location = self.workout_set.location
                self.compiled_live_set.execution_date = self.workout_set.execution_date
                self._refresh_local_history_tree()
                self.display_stack.setCurrentIndex(1)
                self.lbl_coach_status.setStyleSheet(
                    "color: #00cc66; font-weight: bold;"
                )
                self.lbl_coach_status.setText(
                    f"Trening zakończony! Suma powtórzeń: {len(self.compiled_live_set.repetitions)}. Możesz teraz zapisać serię."
                )

            self._toggle_menu_buttons(enabled=True)
            self._restart_passive_preview()

    def _refresh_local_history_tree(self):
        if not self.compiled_live_set:
            return

        total, correct, faulty = self.compiled_live_set.summarize_set()

        mapped_reps = []
        for r in self.compiled_live_set.repetitions:
            mapped_reps.append(
                (
                    r.execution_speed_seconds,
                    r.quality_status,
                    1 if r.error_too_shallow else 0,
                    1 if r.error_too_far_from_chair else 0,
                    1 if r.error_lacks_tempo_control else 0,
                )
            )

        cache_contract = {
            "metadata": {
                "date": self.compiled_live_set.execution_date,
                "location": self.compiled_live_set.location,
                "duration": self.compiled_live_set.duration_seconds,
                "total": total,
                "correct": correct,
                "faulty": faulty,
            },
            "repetitions": mapped_reps,
        }
        self.history_preview_widget.populate_data([cache_contract])

    def _save_set_to_database(self):
        if not self.compiled_live_set:
            QMessageBox.warning(
                self.main_container,
                "Zapis przerwany",
                "Brak danych serii. Uruchom i zatrzymaj trening, aby przechwycić powtórzenia.",
            )
            return

        from PySide6.QtWidgets import QFileDialog

        db_path, _ = QFileDialog.getSaveFileName(
            self.main_container,
            "Wybierz lub utwórz plik bazy danych SQLite",
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

            self.compiled_live_set.location = self.workout_set.location
            self.compiled_live_set.execution_date = self.workout_set.execution_date

            window.db_module.request_set_save(self.compiled_live_set)

            QMessageBox.information(
                self.main_container,
                "Sukces",
                f"Seria treningowa została pomyślnie dopisana do bazy danych:\n{os.path.basename(db_path)}",
            )

            self.compiled_live_set = None
            self.display_stack.setCurrentIndex(0)
            self.lbl_coach_status.setStyleSheet("color: #ffcc00; font-weight: bold;")
            self.lbl_coach_status.setText(
                "Zapisano pomyślnie. Skonfiguruj kamery dla nowej serii."
            )
            self._restart_passive_preview()

    def _toggle_menu_buttons(self, enabled: bool):
        window = self.main_container.window()
        if window and hasattr(window, "menu_stack"):
            active_card = window.menu_stack.currentWidget()
            if active_card:
                for btn in active_card.findChildren(QPushButton):
                    if (
                        "Wróć" not in btn.text()
                        and "Zatrzymaj" not in btn.text()
                        and "Zapisz" not in btn.text()
                    ):
                        btn.setEnabled(enabled)

    def _on_back_clicked(self):
        if self.preview_thread and self.preview_thread.isRunning():
            self.preview_thread.stop()
        if self.live_thread and self.live_thread.isRunning():
            self.live_thread.stop()
            self.live_thread.wait()

        self.compiled_live_set = None
        self.display_stack.setCurrentIndex(0)
        self.navigator_cb("main_page")
