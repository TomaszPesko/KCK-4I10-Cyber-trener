import json  # Import wbudowanego modułu JSON
from datetime import datetime

from PySide6.QtCore import QDateTime, QObject, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Importy klas danych z Twojego projektu
from src.include.set_data import Repetition, WorkoutSet
from src.menuModule.date_dialog import DateTimeDialog
from src.menuModule.manual_set_widget import (
    DurationDialog,
    ManualPreviewWidget,
    RepetitionDialog,
    TrainingDataHistoryWidget,
)
from src.menuModule.menu import Screen
from src.menuModule.progress_chart_widget import ProgressChartWidget
from src.menuModule.video_player import VideoAnalysisThread, VideoDisplayWidget


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


class LoadSetScreen(Screen):
    def __init__(self, navigator_cb):
        self.main_container = QWidget()
        main_layout = QVBoxLayout(self.main_container)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Domain module instance setup
        self.workout_set = WorkoutSet(location="None", duration=0)

        # Display manager stacked layout
        self.display_stack = QStackedWidget()
        main_layout.addWidget(self.display_stack)

        # View State 1: Active native Tree structure preview canvas
        self.history_preview_widget = TrainingDataHistoryWidget()
        self.display_stack.addWidget(self.history_preview_widget)

        # View State 2: Active computer vision video frame pipeline
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

        # Target video file selectors
        front_txt = f"📸 Front: {self._get_filename_or_empty(self.front_video_path)}"
        self.add_option(front_txt, self._select_front_video)

        side_txt = f"📸 Side: {self._get_filename_or_empty(self.side_video_path)}"
        self.add_option(side_txt, self._select_side_video)

        # Target serialization metadata bindings
        self.add_option(f"📍 Location: {self.workout_set.location}", self._set_location)
        self.add_option(
            f"📅 Timestamp: {self.workout_set.execution_date[:16]}", self._set_datetime
        )

        # Interactive controls
        self.add_option("📊 Show Statistics (Tree)", self._show_static_stats)
        self.add_option("⚙️ Run AR Analysis View", self._start_video_analysis)
        self.add_option("💾 Save Set to Database", self._save_set_to_database)
        self.add_option("⬅️ Back", self._on_back_clicked)

    def _get_filename_or_empty(self, path):
        import os

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
        """Processes source data pipelines to instantly populate metrics without blocking UI loops."""
        if not self.front_video_path and not self.side_video_path:
            return

        from src.menuModule.video_player import run_fast_background_analysis

        extracted_reps = run_fast_background_analysis(
            self.front_video_path, self.side_video_path
        )

        self.workout_set.repetitions.clear()
        for rep_tuple in extracted_reps:
            # rep_tuple map: (speed, quality, shallow, far, tempo)
            rep_obj = Repetition(
                speed=rep_tuple[0],
                quality=rep_tuple[1],
                shallow=bool(rep_tuple[2]),
                far=bool(rep_tuple[3]),
                tempo=bool(rep_tuple[4]),
            )
            # Assign properties explicitly to guarantee backend module compatibility
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
        """Transforms active runtime properties into native cached variants matching the new multi-flag schema."""
        total, correct, faulty = self.workout_set.summarize_set()

        mapped_reps = []
        for r in self.workout_set.repetitions:
            # Match the exact column positions expected by TrainingDataHistoryWidget:
            # Index 2: Speed, Index 3: Status, Index 4: Shallow, Index 5: Far, Index 6: Tempo
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
        """Prompts for target storage paths and forwards compiled objects to the async worker."""
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


class AnalyzeProgressScreen(Screen):

    def __init__(self, navigator_cb, load_data_action_cb, get_db_connection_cb=None):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)

        # UI Label - Kept in Polish
        lbl_info = QLabel("Centrum Statystyk i Historii Treningu")
        lbl_info.setStyleSheet(
            "color: #00cc66; font-size: 20px; font-weight: bold; margin-bottom: 5px;"
        )
        lbl_info.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_info)

        # Widget stack switcher layout (Tree vs QtCharts)
        self.display_stack = QStackedWidget()

        # Canvas View 1: History breakdown structure (Tree View)
        self.history_widget = TrainingDataHistoryWidget()
        self.display_stack.addWidget(self.history_widget)

        # Canvas View 2: Native analytics presentation panels (QtCharts View)
        self.chart_widget = ProgressChartWidget()
        self.display_stack.addWidget(self.chart_widget)

        layout.addWidget(self.display_stack)

        super().__init__(container)

        self.load_data_cb = load_data_action_cb
        self.get_db_conn = get_db_connection_cb
        self.cached_sets_data = []

        # Context side navigation option configurations - Polish UI Labels
        self.add_option("Wczytaj dane treningowe", self._load_training_data)
        self.add_option("Jakość serii", self._analyze_set_quality)
        self.add_option("Ilość powtórzeń", self._analyze_reps_count)
        self.add_option("Czas trwania serii", self._analyze_duration)
        self.add_option("Liczba serii w ciągu dnia", self._analyze_sets_per_day)
        self.add_option("Pokaż historię (Drzewo)", self._show_history_tree)
        self.add_option("Wróć", lambda: navigator_cb("main_page"))

    def _load_training_data(self):
        """Triggers system prompts to load local SQLite files and cleans runtime buffers completely."""
        file_path, _ = QFileDialog.getOpenFileName(
            self.content_widget,
            "Wybierz plik bazy danych z treningami",
            "",
            "Baza danych SQLite (*.db *.sqlite);;Wszystkie pliki (*)",
        )

        if not file_path:
            return

        # CRITICAL FIX: Forcefully reset and clear old dataset lists before loading the new database file
        self.cached_sets_data.clear()
        self.history_widget.clear()
        self.chart_widget.clear_chart()
        self._show_history_tree()

        loading_item = QTreeWidgetItem(self.history_widget)
        loading_item.setText(0, "⌛ Wczytywanie danych z bazy... Proszę czekać.")
        loading_item.setForeground(0, QBrush(QColor("#ffcc00")))

        if self.load_data_cb:
            self.load_data_cb(file_path)

    def handle_async_data_loaded(self, raw_sets_data):
        """Asynchronous data stream reception handling target routine slot."""
        # If it's a single set transaction (Dict or Tuple)
        if isinstance(raw_sets_data, (dict, tuple)) and not isinstance(
            raw_sets_data, list
        ):
            exec_date = (
                raw_sets_data.get("metadata", {}).get("date")
                if isinstance(raw_sets_data, dict)
                else raw_sets_data[1]
            )

            is_duplicate = False
            for record in self.cached_sets_data:
                existing_date = (
                    record.get("metadata", {}).get("date")
                    if isinstance(record, dict)
                    else record[1]
                )
                if existing_date == exec_date:
                    is_duplicate = True
                    break

            if not is_duplicate:
                self.cached_sets_data.append(raw_sets_data)

        # If it's an integrated database dump block (List)
        elif isinstance(raw_sets_data, list):
            if raw_sets_data and isinstance(raw_sets_data[0], (dict, tuple)):
                # CRITICAL FIX: Overwrite cache array directly on total bulk updates to prevent file mixing
                self.cached_sets_data = list(raw_sets_data)
            else:
                if raw_sets_data not in self.cached_sets_data:
                    self.cached_sets_data.append(raw_sets_data)

        # Force UI update with freshly synced values
        if self.cached_sets_data:
            self.history_widget.populate_data(self.cached_sets_data)

    def _check_data_ready(self) -> bool:
        """Verifies buffer presence before routing visualization calculations."""
        if not self.cached_sets_data:
            self.display_stack.setCurrentWidget(self.chart_widget)
            self.chart_widget.clear_chart()
            self.chart_widget.chart.setTitle(
                "Brak danych! Najpierw kliknij 'Wczytaj dane treningowe' i wybierz plik bazy."
            )
            self.chart_widget.chart.setTitleBrush(QBrush(QColor("#cc0000")))
            return False
        return True

    def _show_history_tree(self):
        self.display_stack.setCurrentWidget(self.history_widget)

    def _analyze_set_quality(self):
        """Calculates fine-grained performance indices based on composite non-error point aggregates."""
        if not self._check_data_ready():
            return

        self.display_stack.setCurrentWidget(self.chart_widget)
        chart_data = []

        for row in self.cached_sets_data:
            meta = row["metadata"]
            repetitions = row.get("repetitions", [])

            if len(repetitions) > 0:
                total_set_percentage = 0.0
                for rep in repetitions:
                    if isinstance(rep, dict):
                        errors_map = rep.get("errors", {})
                        shallow = 1 if bool(errors_map.get("legs_bent", False)) else 0
                        far = (
                            1
                            if (
                                bool(errors_map.get("too_narrow", False))
                                or bool(errors_map.get("too_wide", False))
                            )
                            else 0
                        )
                        tempo = (
                            1 if bool(errors_map.get("bad_torso_angle", False)) else 0
                        )
                    else:
                        shallow = int(rep[4]) if len(rep) > 4 else 0
                        far = int(rep[5]) if len(rep) > 5 else 0
                        tempo = int(rep[6]) if len(rep) > 6 else 0

                    active_errors_count = shallow + far + tempo
                    rep_percentage = ((3.0 - active_errors_count) / 3.0) * 100.0
                    total_set_percentage += rep_percentage

                calculated_set_average = total_set_percentage / len(repetitions)
                chart_data.append((meta["date"], calculated_set_average))
            else:
                if meta["total"] > 0:
                    ratio_percentage = (meta["correct"] / meta["total"]) * 100.0
                    chart_data.append((meta["date"], ratio_percentage))

        chart_data.sort(key=lambda x: x[0])
        self.chart_widget.display_line_chart(
            data=chart_data,
            title="Analiza Postępów: Procentowa Jakość Wykonania Powtórzeń",
            y_label="Średnia dokładność serii (%)",
            is_percentage=True,
        )

    def _analyze_reps_count(self):
        if not self._check_data_ready():
            return

        self.display_stack.setCurrentWidget(self.chart_widget)

        chart_data = [
            (row["metadata"]["date"], row["metadata"]["total"])
            for row in self.cached_sets_data
        ]
        chart_data.sort(key=lambda x: x[0])

        self.chart_widget.display_line_chart(
            data=chart_data,
            title="Analiza Postępów: Liczba Powtórzeń w Seriach",
            y_label="Suma powtórzeń (reps)",
        )

    def _analyze_duration(self):
        if not self._check_data_ready():
            return

        self.display_stack.setCurrentWidget(self.chart_widget)

        chart_data = [
            (row["metadata"]["date"], row["metadata"]["duration"])
            for row in self.cached_sets_data
        ]
        chart_data.sort(key=lambda x: x[0])

        self.chart_widget.display_line_chart(
            data=chart_data,
            title="Analiza Postępów: Czas Trwania Serii",
            y_label="Czas (sekundy)",
        )

    def _analyze_sets_per_day(self):
        if not self._check_data_ready():
            return

        self.display_stack.setCurrentWidget(self.chart_widget)

        daily_counts = {}
        for row in self.cached_sets_data:
            exec_date = row["metadata"]["date"]
            if exec_date and len(exec_date) >= 10:
                date_only = exec_date[:10]
                daily_counts[date_only] = daily_counts.get(date_only, 0) + 1

        sorted_daily_data = sorted(daily_counts.items())
        self.chart_widget.display_bar_chart(
            data=sorted_daily_data,
            title="Analiza Częstotliwości: Liczba Serii Wykonanych w Ciągu Dnia",
            y_label="Liczba serii",
        )


class ManualDefinitionScreen(Screen, QObject):
    # Signal emitted to the main execution controller to commit a completed manual WorkoutSet instance
    save_requested = Signal(object)

    def __init__(self, navigator_cb, parent_widget):
        # Explicit QObject initialization required under multiple inheritance architectures in PySide
        QObject.__init__(self)
        self.parent_widget = parent_widget
        self.navigator_cb = navigator_cb

        self.manual_set = WorkoutSet(location="", duration=0)
        self.manual_set.execution_date = ""

        self.manual_preview = ManualPreviewWidget()
        super().__init__(self.manual_preview)

        # Dynamic side menu option initializations
        self.add_option("📍 Location", self._set_manual_location)
        self.add_option("⏱ Duration Delta", self._set_manual_duration)
        self.add_option("📅 Timestamp", self._set_manual_datetime)
        self.add_option("＋ Append Repetition", self._add_manual_repetition)
        self.add_option("📥 Import from JSON Structure", self._import_from_json)
        self.add_option("💾 Commit Set to Database", self._save_manual_to_db)
        self.add_option("⬅ Back", lambda: self.navigator_cb("create_set"))

        self._refresh_right_preview()

    def reset_set(self):
        """Restores core parameters to initial clean baseline properties."""
        self.manual_set = WorkoutSet(location="", duration=0)
        self.manual_set.execution_date = ""
        self._refresh_right_preview()

    def _refresh_right_preview(self):
        location_label = self.manual_set.location if self.manual_set.location else "___"
        if self.manual_set.duration_seconds > 0:
            minutes = self.manual_set.duration_seconds // 60
            seconds = self.manual_set.duration_seconds % 60
            duration_label = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
        else:
            duration_label = "___"

        timestamp_label = (
            self.manual_set.execution_date if self.manual_set.execution_date else "___"
        )
        self.manual_preview.update_view(
            location_label, duration_label, timestamp_label, self.manual_set.repetitions
        )

    def _set_manual_location(self):
        text, ok = QInputDialog.getText(
            self.parent_widget,
            "Session Configuration",
            "Enter location label:",
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
        if dialog.exec() == DurationDialog.Accepted:
            self.manual_set.execution_date = dialog.get_date_string()
            self._refresh_right_preview()

    def _add_manual_repetition(self):
        dialog = RepetitionDialog(self.parent_widget)
        if dialog.exec() == RepetitionDialog.Accepted:
            self.manual_set.add_repetition(dialog.get_data())
            self._refresh_right_preview()

    def _import_from_json(self):
        """
        Parses multi-profile JSON arrays and maps them directly onto the SQLite architecture.
        Elimitnates intermediate modal rendering loops completely.
        """
        import sqlite3

        # 1. Select the mock generation file target
        json_path, _ = QFileDialog.getOpenFileName(
            self.content_widget,
            "Select JSON Configuration Source",
            "",
            "JSON Structured Profiles (*.json)",
        )
        if not json_path:
            return

        # 2. Designate destination file pipeline target
        db_path, _ = QFileDialog.getSaveFileName(
            self.content_widget,
            "Select Target SQLite Destination Database (.db)",
            "",
            "Database Engines (*.db *.sqlite);;All Files (*)",
        )
        if not db_path:
            return

        db_connection = None
        try:
            with open(json_path, "r", encoding="utf-8") as file_stream:
                parsed_json = json.load(file_stream)

            if isinstance(parsed_json, dict):
                series_data_list = [parsed_json]
            elif isinstance(parsed_json, list):
                series_data_list = parsed_json
            else:
                raise ValueError(
                    "Corrupted schema architecture payload wrapper detected."
                )

            # 3. Direct SQL engine connection routine
            db_connection = sqlite3.connect(db_path)
            db_cursor = db_connection.cursor()
            db_cursor.execute("PRAGMA foreign_keys = ON;")

            # Initialize structures explicitly
            db_cursor.execute("""
                CREATE TABLE IF NOT EXISTS sets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_date TEXT, location TEXT, duration_seconds INTEGER,
                    total_reps INTEGER, correct_reps INTEGER, faulty_reps INTEGER
                )""")
            db_cursor.execute("""
                CREATE TABLE IF NOT EXISTS repetitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, set_id INTEGER,
                    execution_speed_seconds REAL, quality_status TEXT,
                    error_too_shallow INTEGER, error_too_far_from_chair INTEGER, error_lacks_tempo_control INTEGER,
                    FOREIGN KEY(set_id) REFERENCES sets(id) ON DELETE CASCADE
                )""")

            saved_counter = 0

            for structure_item in series_data_list:
                metadata = structure_item.get("metadata", {})
                extracted_date = metadata.get("date", "")
                extracted_loc = metadata.get("location", "JSON Bulk Import")
                extracted_dur = int(metadata.get("duration_seconds", 0))

                if not extracted_date:
                    extracted_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                repetitions_payload = structure_item.get("repetitions", [])
                if not repetitions_payload:
                    continue

                total_reps = len(repetitions_payload)
                correct_reps = sum(
                    1 for r in repetitions_payload if r.get("quality") == "Correct"
                )
                faulty_reps = total_reps - correct_reps

                db_cursor.execute(
                    """
                    INSERT INTO sets (execution_date, location, duration_seconds, total_reps, correct_reps, faulty_reps)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        extracted_date,
                        extracted_loc,
                        extracted_dur,
                        total_reps,
                        correct_reps,
                        faulty_reps,
                    ),
                )

                generated_set_id = db_cursor.lastrowid

                # Unify multiple independent error conditions concurrently per entry cycle
                for single_rep in repetitions_payload:
                    speed = float(single_rep.get("speed", 2.2))
                    quality_status = single_rep.get("quality", "Correct")
                    error_flags = single_rep.get("errors", {})

                    # Direct assignment mapping layout
                    error_too_shallow = (
                        1 if bool(error_flags.get("legs_bent", False)) else 0
                    )
                    error_too_far_from_chair = (
                        1
                        if (
                            bool(error_flags.get("too_narrow", False))
                            or bool(error_flags.get("too_wide", False))
                        )
                        else 0
                    )
                    error_lacks_tempo_control = (
                        1 if bool(error_flags.get("bad_torso_angle", False)) else 0
                    )

                    db_cursor.execute(
                        """
                        INSERT INTO repetitions (
                            set_id, execution_speed_seconds, quality_status, 
                            error_too_shallow, error_too_far_from_chair, error_lacks_tempo_control
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            generated_set_id,
                            speed,
                            quality_status,
                            error_too_shallow,
                            error_too_far_from_chair,
                            error_lacks_tempo_control,
                        ),
                    )

                saved_counter += 1

            db_connection.commit()
            self.reset_set()

            # Direct tracking sync alerts upstream to the core context application instance
            if hasattr(self.parent_widget, "db_module"):
                self.parent_widget.db_module.db_path = db_path
                if hasattr(self.parent_widget.db_module, "request_all_data"):
                    self.parent_widget.db_module.request_all_data()

            QMessageBox.information(
                self.parent_widget,
                "Import Complete",
                f"Successfully extracted training profiles!\n"
                f"Committed {saved_counter} sets directly to database file:\n{db_path}",
            )

        except Exception as e:
            if db_connection:
                db_connection.rollback()
            QMessageBox.critical(
                self.parent_widget,
                "Serialization Error",
                f"Failed to record data blocks on storage targets:\n{str(e)}",
            )
        finally:
            if db_connection:
                db_connection.close()

    def _save_manual_to_db(self):
        if not self.manual_set.repetitions:
            QMessageBox.warning(
                self.parent_widget,
                "Verification Halt",
                "Cannot save an empty sequence containing zero repetitions.",
            )
            return

        if not self.manual_set.location:
            self.manual_set.location = "Home"
        if not self.manual_set.execution_date:
            self.manual_set.execution_date = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        self.save_requested.emit(self.manual_set)
