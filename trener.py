import sqlite3
import os
import cv2
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk

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

    cursor.execute("""
    INSERT INTO series (time, place, description)
    VALUES (?, ?, ?)
    """, (time, place, description))

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

    cursor.execute("""
    SELECT COUNT(*) FROM perspectives
    WHERE series_id=? AND type=?
    """, (series_id, perspective_type))

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

    cursor.execute("""
    INSERT INTO perspectives (series_id, type, file_path, start_time, end_time)
    VALUES (?, ?, ?, ?, ?)
    """, (series_id, perspective_type, video_path, start_time, end_time))

    conn.commit()
    conn.close()


def delete_perspective(series_id, perspective_type):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM perspectives
    WHERE series_id=? AND type=?
    """, (series_id, perspective_type))

    conn.commit()
    conn.close()


def select_perspective(series_id):
    if count_perspectives(series_id) >= 2:
        messagebox.showerror("Error", "Max 2 reached")
        return

    file_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4")])
    if not file_path:
        return

    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        messagebox.showerror("Error", "Cannot open video")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    window = tk.Toplevel()
    window.title("Select Range")

    video_label = tk.Label(window)
    video_label.pack()

    def show_frame(frame_idx):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            return

        frame = cv2.resize(frame, (600, 400))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        img = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(image=img)

        video_label.imgtk = imgtk
        video_label.configure(image=imgtk)

    start_scale = tk.Scale(
        window,
        from_=0,
        to=duration,
        resolution=0.1,
        orient="horizontal"
    )
    start_scale.pack(fill="x")

    end_scale = tk.Scale(
        window,
        from_=0,
        to=duration,
        resolution=0.1,
        orient="horizontal"
    )
    end_scale.set(duration)
    end_scale.pack(fill="x")

    def on_start_move(val):
        frame = int(float(val) * fps)
        show_frame(frame)

    def on_end_move(val):
        frame = int(float(val) * fps)
        show_frame(frame)

    start_scale.config(command=on_start_move)
    end_scale.config(command=on_end_move)

    perspective = ttk.Combobox(window, values=["front", "side"])
    perspective.current(0)
    perspective.pack()

    def submit():
        try:
            start_time = float(start_scale.get())
            end_time = float(end_scale.get())

            add_perspective(
                series_id,
                file_path,
                perspective.get(),
                start_time,
                end_time
            )

            cap.release()
            messagebox.showinfo("OK", "Saved")
            window.destroy()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    tk.Button(window, text="Save", command=submit).pack()

    show_frame(0)

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
    root.state("zoomed")

    series_id = create_series("2026-05-04")

    tk.Button(root, text="Add", command=lambda: select_perspective(series_id), height=3, width=20).pack(pady=20)
    tk.Button(root, text="Delete", command=lambda: delete_window(series_id), height=3, width=20).pack(pady=20)
    tk.Button(root, text="Save & Exit", command=lambda: save_and_exit(root, series_id), height=3, width=20).pack(pady=20)
    tk.Button(root, text="Exit", command=lambda: exit_app(root), height=3, width=20).pack(pady=20)

    root.mainloop()