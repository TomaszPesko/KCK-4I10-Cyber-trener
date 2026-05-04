import os
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2

DB_NAME = "series.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS series (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time TEXT NOT NULL,
        place TEXT,
        description TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS perspectives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        series_id INTEGER,
        type TEXT,
        file_path TEXT,
        start_time REAL,
        end_time REAL
    )
    """)

    conn.commit()
    conn.close()


def create_series(time, place="", description=""):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
    INSERT INTO series (time, place, description)
    VALUES (?, ?, ?)
    """,
        (time, place, description),
    )

    series_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return series_id


def count_perspectives(series_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM perspectives WHERE series_id=?", (series_id,))
    count = cursor.fetchone()[0]

    conn.close()
    return count


def add_perspective(series_id, video_path, perspective_type, start_time, end_time):
    if count_perspectives(series_id) >= 2:
        raise ValueError("Max 2 perspectives")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
    SELECT COUNT(*) FROM perspectives
    WHERE series_id=? AND type=?
    """,
        (series_id, perspective_type),
    )

    if cursor.fetchone()[0] > 0:
        conn.close()
        raise ValueError("Already exists")

    if not os.path.exists(video_path):
        raise ValueError("No file")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Cannot open")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = frames / fps

    if start_time < 0 or end_time > duration or start_time >= end_time:
        raise ValueError("Bad time")

    cap.release()

    cursor.execute(
        """
    INSERT INTO perspectives (series_id, type, file_path, start_time, end_time)
    VALUES (?, ?, ?, ?, ?)
    """,
        (series_id, perspective_type, video_path, start_time, end_time),
    )

    conn.commit()
    conn.close()


def delete_perspective(series_id, perspective_type):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
    DELETE FROM perspectives
    WHERE series_id=? AND type=?
    """,
        (series_id, perspective_type),
    )

    conn.commit()
    conn.close()


def select_perspective(series_id):
    if count_perspectives(series_id) >= 2:
        messagebox.showerror("Error", "Max 2 reached")
        return

    file_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4")])
    if not file_path:
        return

    window = tk.Toplevel()
    window.title("Add")

    tk.Label(window, text="Type").grid(row=0, column=0)
    perspective = ttk.Combobox(window, values=["front", "side"])
    perspective.current(0)
    perspective.grid(row=0, column=1)

    tk.Label(window, text="Start").grid(row=1, column=0)
    start_entry = tk.Entry(window)
    start_entry.insert(0, "0")
    start_entry.grid(row=1, column=1)

    tk.Label(window, text="End").grid(row=2, column=0)
    end_entry = tk.Entry(window)
    end_entry.insert(0, "10")
    end_entry.grid(row=2, column=1)

    def submit():
        try:
            add_perspective(
                series_id,
                file_path,
                perspective.get(),
                float(start_entry.get()),
                float(end_entry.get()),
            )
            messagebox.showinfo("OK", "Saved")
            window.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    tk.Button(window, text="Save", command=submit).grid(row=3, column=0, columnspan=2)


def delete_window(series_id):
    window = tk.Toplevel()
    window.title("Delete")

    tk.Label(window, text="Type").pack()

    perspective = ttk.Combobox(window, values=["front", "side"])
    perspective.current(0)
    perspective.pack()

    def submit():
        delete_perspective(series_id, perspective.get())
        messagebox.showinfo("OK", "Deleted")
        window.destroy()

    tk.Button(window, text="Delete", command=submit).pack()


def exit_app(root):
    root.destroy()


def save_and_exit(root, series_id):
    if count_perspectives(series_id) < 1:
        messagebox.showerror("Error", "Add at least 1 perspective")
        return
    root.destroy()


if __name__ == "__main__":
    init_db()

    root = tk.Tk()
    root.attributes("-zoomed", True)

    series_id = create_series("2026-05-04")

    tk.Button(
        root,
        text="Add",
        command=lambda: select_perspective(series_id),
        height=3,
        width=20,
    ).pack(pady=20)
    tk.Button(
        root,
        text="Delete",
        command=lambda: delete_window(series_id),
        height=3,
        width=20,
    ).pack(pady=20)
    tk.Button(
        root,
        text="Save & Exit",
        command=lambda: save_and_exit(root, series_id),
        height=3,
        width=20,
    ).pack(pady=20)
    tk.Button(
        root, text="Exit", command=lambda: exit_app(root), height=3, width=20
    ).pack(pady=20)

    root.mainloop()

