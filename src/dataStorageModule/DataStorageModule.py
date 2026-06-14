# ==> ./dataStorageModule/DataStorageModule.py <==
import queue
import sqlite3
import threading

from PySide6.QtCore import QObject, Signal


class DatabaseSignals(QObject):
    """Signals used to safely transport DB data back to the PySide6 main loop."""

    data_loaded = Signal(list)


class DatabaseModule(threading.Thread):
    def __init__(self, db_path="cyber_trainer.db"):
        super().__init__()
        self.db_path = db_path
        self.task_queue = queue.Queue()
        self.daemon = True
        self.conn = None
        self.signals = DatabaseSignals()

    def _initialize_db(self):
        """Creates synchronized domain structure metrics if tables do not exist."""
        self.conn.execute("PRAGMA foreign_keys = ON;")

        # Session sets overview table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_date TEXT, 
                location TEXT, 
                duration_seconds INTEGER,
                total_reps INTEGER, 
                correct_reps INTEGER, 
                faulty_reps INTEGER
            )""")

        # Unified tracking structure with explicit boolean binary flag errors
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS repetitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                set_id INTEGER,
                execution_speed_seconds REAL, 
                quality_status TEXT,
                error_too_shallow INTEGER, 
                error_too_far_from_chair INTEGER, 
                error_lacks_tempo_control INTEGER,
                FOREIGN KEY(set_id) REFERENCES sets(id) ON DELETE CASCADE
            )""")
        self.conn.commit()

    def run(self):
        self.conn = sqlite3.connect(self.db_path)
        self._initialize_db()

        try:
            while True:
                task = self.task_queue.get()
                if task is None:
                    break

                task_type, data, *callback = task

                try:
                    if task_type == "SAVE_SET":
                        self._save_set_to_db(data)
                    elif task_type == "GET_STATISTICS":
                        result = self._get_statistics_from_db()
                        if callback:
                            callback[0](result)
                    elif task_type == "FETCH_ALL_DATA":
                        result = self._fetch_all_sets_and_reps()
                        self.signals.data_loaded.emit(result)

                except Exception as e:
                    print(f"[Database Error] Routine crash inside {task_type}: {e}")
                finally:
                    self.task_queue.task_done()
        finally:
            if self.conn:
                self.conn.close()

    def _save_set_to_db(self, workout_set):
        """Extracts runtime set details and logs unified cross-perspective repetitions."""
        total_reps, correct_reps, faulty_reps = workout_set.summarize_set()
        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT INTO sets (execution_date, location, duration_seconds, total_reps, correct_reps, faulty_reps)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                workout_set.execution_date,
                workout_set.location,
                workout_set.duration_seconds,
                total_reps,
                correct_reps,
                faulty_reps,
            ),
        )
        set_id = cursor.lastrowid

        for r in workout_set.repetitions:
            # Enforce 1/0 values across all mapped error parameters simultaneously
            cursor.execute(
                """
                INSERT INTO repetitions (
                    set_id, execution_speed_seconds, quality_status, 
                    error_too_shallow, error_too_far_from_chair, error_lacks_tempo_control
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    set_id,
                    r.execution_speed_seconds,
                    r.quality_status,
                    1 if getattr(r, "error_too_shallow", False) else 0,
                    1 if getattr(r, "error_too_far_from_chair", False) else 0,
                    1 if getattr(r, "error_lacks_tempo_control", False) else 0,
                ),
            )
        self.conn.commit()

    def _get_statistics_from_db(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*), SUM(total_reps), SUM(correct_reps) FROM sets")
        return cursor.fetchone()

    def _fetch_all_sets_and_reps(self) -> list:
        """Retrieves and packages multi-perspective data sets for the history views."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, execution_date, location, duration_seconds, total_reps, correct_reps, faulty_reps FROM sets ORDER BY id DESC"
        )
        sets_rows = cursor.fetchall()

        all_data = []
        for s_row in sets_rows:
            set_id = s_row[0]

            cursor.execute(
                """
                SELECT execution_speed_seconds, quality_status, error_too_shallow, error_too_far_from_chair, error_lacks_tempo_control 
                FROM repetitions WHERE set_id = ?
                """,
                (set_id,),
            )
            reps_rows = cursor.fetchall()

            all_data.append(
                {
                    "metadata": {
                        "date": s_row[1],
                        "location": s_row[2],
                        "duration": s_row[3],
                        "total": s_row[4],
                        "correct": s_row[5],
                        "faulty": s_row[6],
                    },
                    "repetitions": reps_rows,
                }
            )
        return all_data

    # --- PUBLIC API ---
    def request_set_save(self, workout_set):
        self.task_queue.put(("SAVE_SET", workout_set))

    def request_statistics(self, receiving_function):
        self.task_queue.put(("GET_STATISTICS", None, receiving_function))

    def request_all_data(self):
        self.task_queue.put(("FETCH_ALL_DATA", None))
