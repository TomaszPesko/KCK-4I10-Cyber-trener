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
    QVBoxLayout,
    QWidget,
)

from src.dataStorageModule.DataStorageModule import DatabaseModule
from src.menuModule.menu import Screen
from src.menuModule.widgets.camera_live_thread import CameraLiveThread
from src.menuModule.widgets.camera_preview_thread import CameraPreviewThread
from src.menuModule.widgets.date_dialog import DateTimeDialog
from src.menuModule.widgets.video_player import VideoDisplayWidget
from src.videoAnalysisModule.VideoAnalyzer import VideoAnalyzer


class MockWorkoutSet:
    def __init__(self):
        self.location = "Siłownia"
        self.execution_date = QDateTime.currentDateTime().toString(
            "yyyy-MM-dd HH:mm:ss"
        )
        self.duration_seconds = 45
        self.repetitions = []


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
        self.workout_set = MockWorkoutSet()

        setup_panel = QHBoxLayout()

        setup_panel.addWidget(QLabel("Kamera przód:"))
        self.combo_front = QComboBox()
        self.combo_front.addItems(["Brak", "Kamera 0", "Kamera 1"])
        self.combo_front.setCurrentIndex(0)  # Start jako brak
        self.combo_front.currentIndexChanged.connect(self._restart_pasywny_podglad)
        setup_panel.addWidget(self.combo_front)

        setup_panel.addWidget(QLabel("Kamera bok:"))
        self.combo_side = QComboBox()
        self.combo_side.addItems(["Brak", "Kamera 0", "Kamera 1", "Kamera 2"])
        self.combo_side.setCurrentIndex(0)  # Start jako brak
        self.combo_side.currentIndexChanged.connect(self._restart_pasywny_podglad)
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

        self.video_display = VideoDisplayWidget()
        self.video_display.setFixedHeight(380)
        main_layout.addWidget(self.video_display)

        super().__init__(self.main_container)
        self._build_menu()

    def _build_menu(self):
        self.options.clear()
        self.add_option("▶️ Uruchom Trenera AI", self._start_live_workout)
        self.add_option("🛑 Zatrzymaj Analizę", self._stop_live_workout)

        # Metadane zintegrowane w menu bocznym aplikacji
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

    def _restart_pasywny_podglad(self):
        """Zapewnia ciągłe renderowanie strumieni wideo w czasie spoczynku."""
        if self.live_thread and self.live_thread.isRunning():
            return

        if self.preview_thread and self.preview_thread.isRunning():
            self.preview_thread.stop()

        has_front = self.combo_front.currentText() != "Brak"
        has_side = self.combo_side.currentText() != "Brak"

        self.video_display.set_modes(has_front, has_side)

        if has_front or has_side:
            self.preview_thread = CameraPreviewThread(
                self.combo_front.currentIndex(),
                self.combo_side.currentIndex(),
                has_front,
                has_side,
            )
            self.preview_thread.frame_processed.connect(
                self.video_display.update_frames
            )
            self.preview_thread.start()

    def _start_live_workout(self):
        if self.live_thread and self.live_thread.isRunning():
            return

        # Wyłączamy pasywny podgląd, by zwolnić deskryptory urządzeń dla analizatora MediaPipe
        if self.preview_thread and self.preview_thread.isRunning():
            self.preview_thread.stop()

        has_front = self.combo_front.currentText() != "Brak"
        has_side = self.combo_side.currentText() != "Brak"

        if not has_front and not has_side:
            QMessageBox.critical(
                self.main_container,
                "Błąd",
                "Wybierz przynajmniej jedną działającą kamerę.",
            )
            self._restart_pasywny_podglad()
            return

        front_idx = self.combo_front.currentIndex()
        side_idx = self.combo_side.currentIndex()

        self.video_display.set_modes(has_front, has_side)
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
                source_front="Live_Cam",
                source_side="Live_Cam",
                custom_metadata=(
                    self.workout_set.execution_date,
                    self.workout_set.location,
                    self.workout_set.duration_seconds,
                ),
            )

            self._toggle_menu_buttons(enabled=True)
            self.lbl_coach_status.setText(
                "Seria przechwycona. Możesz zsynchronizować dane z bazą SQLite."
            )

            self._restart_pasywny_podglad()

    def _save_set_to_database(self):
        if not self.compiled_live_set:
            QMessageBox.warning(
                self.main_container,
                "Brak danych",
                "Uruchom i zatrzymaj trening, aby przechwycić serię.",
            )
            return

        try:
            self.compiled_live_set.location = self.workout_set.location
            self.compiled_live_set.execution_date = self.workout_set.execution_date

            self.db_module.request_set_save(self.compiled_live_set)

            QMessageBox.information(
                self.main_container,
                "Sukces",
                "Seria na żywo została przekazana do asynchronicznej bazy danych.",
            )
            self.compiled_live_set = None
            self.lbl_coach_status.setText("Zapisano. Gotowy na kolejną serię.")
        except Exception as e:
            QMessageBox.critical(self.main_container, "Błąd", f"Blokada zapisu: {e}")

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
        self.navigator_cb("main_page")
