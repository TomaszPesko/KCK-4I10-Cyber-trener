import json
import sqlite3
from datetime import datetime

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QDialog, QFileDialog, QInputDialog, QLineEdit, QMessageBox

from src.include.set_data import Repetition, WorkoutSet
from src.menuModule.menu import Screen
from src.menuModule.widgets.date_dialog import DateTimeDialog
from src.menuModule.widgets.manual_set_widget import (
    DurationDialog,
    ManualPreviewWidget,
    RepetitionDialog,
)


class ManualDefinitionScreen(Screen, QObject):
    save_requested = Signal(object)

    def __init__(self, navigator_cb, parent_widget):
        QObject.__init__(self)
        self.parent_widget = parent_widget
        self.navigator_cb = navigator_cb

        self.manual_set = WorkoutSet(location="", duration=0)
        self.manual_set.execution_date = ""

        self.manual_preview = ManualPreviewWidget()
        super().__init__(self.manual_preview)

        self.add_option("📍 Location", self._set_manual_location)
        self.add_option("⏱ Duration Delta", self._set_manual_duration)
        self.add_option("📅 Timestamp", self._set_manual_datetime)
        self.add_option("＋ Append Repetition", self._add_manual_repetition)
        self.add_option("📥 Import from JSON Structure", self._import_from_json)
        self.add_option("💾 Commit Set to Database", self._save_manual_to_db)
        self.add_option("⬅ Back", lambda: self.navigator_cb("create_set"))

        self._refresh_right_preview()

    def reset_set(self):
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
        if dialog.exec() == QDialog.Accepted:
            self.manual_set.execution_date = dialog.get_date_string()
            self._refresh_right_preview()

    def _add_manual_repetition(self):
        dialog = RepetitionDialog(self.parent_widget)
        if dialog.exec() == RepetitionDialog.Accepted:
            self.manual_set.add_repetition(dialog.get_data())
            self._refresh_right_preview()

    def _import_from_json(self):
        json_path, _ = QFileDialog.getOpenFileName(
            self.content_widget,
            "Select JSON Configuration Source",
            "",
            "JSON Structured Profiles (*.json)",
        )
        if not json_path:
            return

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

            db_connection = sqlite3.connect(db_path)
            db_cursor = db_connection.cursor()
            db_cursor.execute("PRAGMA foreign_keys = ON;")

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

                for single_rep in repetitions_payload:
                    speed = float(single_rep.get("speed", 2.2))
                    quality_status = single_rep.get("quality", "Correct")
                    error_flags = single_rep.get("errors", {})

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

            if hasattr(self.parent_widget, "db_module"):
                self.parent_widget.db_module.db_path = db_path
                if hasattr(self.parent_widget.db_module, "request_all_data"):
                    self.parent_widget.db_module.request_all_data()

            QMessageBox.information(
                self.parent_widget,
                "Import Complete",
                f"Successfully extracted training profiles!\nCommitted {saved_counter} sets directly to database file:\n{db_path}",
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
