import threading
import time
import tkinter as tk
from multiprocessing import Process, Queue

import cv2
import pyttsx3
import speech_recognition as sr
from PIL import Image, ImageTk

# ====== AUDIO PROCESS ======


def find_best_microphone():
    import pyaudio

    p = pyaudio.PyAudio()

    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if dev["maxInputChannels"] > 0:
            name = dev["name"].lower()
            if "pulse" in name or "microphone" in name:
                return i
    return None


def voice_process(queue):
    import pyttsx3
    import speech_recognition as sr

    recognizer = sr.Recognizer()
    tts = pyttsx3.init()
    tts.setProperty("rate", 150)

    mic_index = find_best_microphone()
    mic = sr.Microphone(device_index=mic_index)

    # kalibracja
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)

    while True:
        try:
            with mic as source:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)

            text = recognizer.recognize_google(audio, language="pl-PL").lower()

            # DEBUG (ważne!)
            print("Rozpoznano:", text)

            if "start" in text:
                print("odczytano start")
                queue.put("start")
                tts.say("start")
                tts.runAndWait()

            elif "stop" in text:
                print("odczytano stop")
                queue.put("stop")
                tts.say("stop")
                tts.runAndWait()

        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            continue
        except sr.RequestError:
            continue
        except Exception as e:
            print("Voice error:", e)


# ====== VIDEO STREAM ======


class VideoStream:
    def __init__(self, source):
        self.cap = cv2.VideoCapture(source)
        self.frame = None
        self.running = True
        self.playing = True
        self.lock = threading.Lock()

        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def update(self):
        while self.running:
            if self.playing:
                ret, frame = self.cap.read()

                if not ret:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                with self.lock:
                    self.frame = frame

            time.sleep(1 / 30)

    def get_frame(self):
        with self.lock:
            return self.frame

    def set_play(self, state: bool):
        self.playing = state

    def stop(self):
        self.running = False
        self.cap.release()


# ====== APP ======


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("E-trener")

        w = int(self.winfo_screenwidth() * 0.7)
        h = int(self.winfo_screenheight() * 0.7)
        self.geometry(f"{w}x{h}")
        self.resizable(False, False)

        self.queue = None
        self.voice_proc = None

        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.frames = {}

        for F in (MainMenu, AddSeriesMenu, LoadFromFile, LiveView):
            frame = F(self.container, self)
            self.frames[F] = frame
            frame.place(relwidth=1, relheight=1)

        self.show_frame(MainMenu)

    def show_frame(self, frame_class):
        frame = self.frames[frame_class]
        frame.tkraise()

    def start_voice(self):
        if self.voice_proc is None:
            self.queue = Queue()
            self.voice_proc = Process(target=voice_process, args=(self.queue,))
            self.voice_proc.daemon = True
            self.voice_proc.start()

    def stop_voice(self):
        if self.voice_proc:
            self.voice_proc.terminate()
            self.voice_proc = None


# ====== MENU ======


class BaseDummy(tk.Frame):
    def __init__(self, parent, controller, title):
        super().__init__(parent)

        tk.Button(
            self, text="←", command=lambda: controller.show_frame(MainMenu)
        ).place(x=10, y=10)

        tk.Label(self, text=title, font=("Arial", 20)).pack(pady=50)


class DummyStats(BaseDummy):
    def __init__(self, parent, controller):
        super().__init__(parent, controller, "Statystyki")


class DummyProgress(BaseDummy):
    def __init__(self, parent, controller):
        super().__init__(parent, controller, "Progres")


class DummyLoadSeries(BaseDummy):
    def __init__(self, parent, controller):
        super().__init__(parent, controller, "Wczytaj serię")


class MainMenu(tk.Frame):
    def __init__(self, parent, ctrl):
        super().__init__(parent)

        tk.Label(self, text="Menu główne", font=("Arial", 20)).pack(pady=20)

        tk.Button(
            self, text="Dodaj serię", command=lambda: ctrl.show_frame(AddSeriesMenu)
        ).pack(pady=5)

        tk.Button(
            self, text="Wczytaj serię", command=lambda: ctrl.show_frame(DummyLoadSeries)
        ).pack(pady=5)

        tk.Button(
            self, text="Statystyki", command=lambda: ctrl.show_frame(DummyStats)
        ).pack(pady=5)

        tk.Button(
            self, text="Progres", command=lambda: ctrl.show_frame(DummyProgress)
        ).pack(pady=5)

        tk.Button(self, text="Wyjście", command=ctrl.quit).pack(pady=20)


class AddSeriesMenu(tk.Frame):
    def __init__(self, parent, ctrl):
        super().__init__(parent)

        tk.Button(self, text="←", command=lambda: ctrl.show_frame(MainMenu)).place(
            x=10, y=10
        )

        tk.Label(self, text="Dodaj serię", font=("Arial", 20)).pack(pady=40)

        tk.Button(
            self, text="Dodaj na żywo", command=lambda: ctrl.show_frame(LiveView)
        ).pack(pady=5)

        tk.Button(
            self, text="Wczytaj z pliku", command=lambda: ctrl.show_frame(LoadFromFile)
        ).pack(pady=5)


# ====== 3 VIDEO PANEL ======


class LoadFromFile(tk.Frame):
    def __init__(self, parent, ctrl):
        super().__init__(parent)
        self.ctrl = ctrl

        # ===== TOP BAR =====
        top = tk.Frame(self, height=50)
        top.pack(fill="x")

        tk.Button(top, text="←", command=lambda: ctrl.show_frame(AddSeriesMenu)).pack(
            side="left", padx=10, pady=10
        )

        tk.Label(top, text="Wczytaj z pliku", font=("Arial", 14)).pack(side="left")

        # ===== VIDEO AREA =====
        video_frame = tk.Frame(self)
        video_frame.pack(fill="both", expand=True)

        self.labels = []
        for i in range(3):
            lbl = tk.Label(video_frame)
            lbl.grid(row=0, column=i, padx=10, pady=10)
            video_frame.grid_columnconfigure(i, weight=1)
            self.labels.append(lbl)

        self.streams = [
            VideoStream("video1.mp4"),
            VideoStream("video2.mp4"),
            VideoStream("video3.mp4"),
        ]

        self.update_gui()

    def update_gui(self):
        for i, s in enumerate(self.streams):
            frame = s.get_frame()
            if frame is not None:
                # ===== KLUCZOWE: zmniejszenie =====
                frame = cv2.resize(frame, (400, 300))

                img = ImageTk.PhotoImage(Image.fromarray(frame))
                self.labels[i].img = img
                self.labels[i].config(image=img)

        self.after(30, self.update_gui)


# ====== LIVE VIEW + VOICE ======


class LiveView(tk.Frame):
    def __init__(self, parent, ctrl):
        super().__init__(parent)
        self.ctrl = ctrl

        tk.Button(self, text="←", command=self.go_back).place(x=10, y=10)

        tk.Label(self, text="Powiedz start/stop", font=("Arial", 14)).pack(pady=10)

        self.label = tk.Label(self)
        self.label.pack()

        self.stream = VideoStream("video1.mp4")

        self.ctrl.start_voice()

        self.running = True
        self.update_gui()
        self.check_queue()

    def update_gui(self):
        frame = self.stream.get_frame()
        if frame is not None:
            img = ImageTk.PhotoImage(Image.fromarray(frame))
            self.label.img = img
            self.label.config(image=img)

        if self.running:
            self.after(30, self.update_gui)

    def check_queue(self):
        if self.ctrl.queue:
            while not self.ctrl.queue.empty():
                cmd = self.ctrl.queue.get()
                if cmd == "start":
                    self.stream.set_play(True)
                elif cmd == "stop":
                    self.stream.set_play(False)

        if self.running:
            self.after(100, self.check_queue)

    def go_back(self):
        self.running = False
        self.stream.stop()
        self.ctrl.stop_voice()
        self.ctrl.show_frame(AddSeriesMenu)


# ====== START ======

if __name__ == "__main__":
    app = App()
    app.mainloop()
