import queue
import sqlite3
import threading
import time


class DataStorageModule(threading.Thread):
    def __init__(self, db_path="cyber_trainer.db"):
        super().__init__()
        self.db_path = db_path
        self.task_queue = queue.Queue()
        self.daemon = (
            True  # Thread will exit automatically when the main application closes
        )
        self._initialize_db()

    def _initialize_db(self):
        """Creates tables if they do not exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_date TEXT, location TEXT, duration_seconds INTEGER,
                    total_reps INTEGER, correct_reps INTEGER, faulty_reps INTEGER
                )""")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS repetitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, set_id INTEGER,
                    execution_speed_seconds REAL, quality_status TEXT,
                    error_too_shallow INTEGER, error_too_far_from_chair INTEGER, error_lacks_tempo_control INTEGER,
                    FOREIGN KEY(set_id) REFERENCES sets(id) ON DELETE CASCADE
                )""")

    def run(self):
        """Main thread loop - waits for tasks from the queue."""
        print("Database module started in a separate thread...")
        while True:
            task = self.task_queue.get()
            if task is None:  # Signal to stop the thread
                break

            task_type, data, *callback = task

            if task_type == "SAVE_SET":
                self._save_set_to_db(data)
            elif task_type == "GET_STATISTICS":
                result = self._get_statistics_from_db()
                if callback:
                    callback[0](result)  # Pass the result back via callback function

            self.task_queue.task_done()

    # --- INTERNAL METHODS OPERATING ON SQL ---
    def _save_set_to_db(self, workout_set: Set):
        total_reps, correct_reps, faulty_reps = workout_set.summarize_set()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 1. Save the set
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

            # 2. Save repetitions assigned to this set
            for r in workout_set.repetitions:
                cursor.execute(
                    """
                    INSERT INTO repetitions (set_id, execution_speed_seconds, quality_status, error_too_shallow, error_too_far_from_chair, error_lacks_tempo_control)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        set_id,
                        r.execution_speed_seconds,
                        r.quality_status,
                        int(r.error_too_shallow),
                        int(r.error_too_far_from_chair),
                        int(r.error_lacks_tempo_control),
                    ),
                )
            conn.commit()
        print(f"-> Saved set ID {set_id} with {total_reps} repetitions.")

    def _get_statistics_from_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Sample simple general statistics
            cursor.execute(
                "SELECT COUNT(*), SUM(total_reps), SUM(correct_reps) FROM sets"
            )
            return cursor.fetchone()

    # --- PUBLIC API (Called by other modules) ---
    def request_set_save(self, workout_set: Set):
        self.task_queue.put(("SAVE_SET", workout_set))

    def request_statistics(self, receiving_function):
        self.task_queue.put(("GET_STATISTICS", None, receiving_function))
