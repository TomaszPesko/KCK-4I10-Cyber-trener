import sys
import threading
import time
from multiprocessing import Process, Queue

import cv2
import pyttsx3
import speech_recognition as sr
from PIL import Image, ImageQt
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from menu import TemplateWindow

# =========================
# VOICE PROCESS (UNCHANGED)
# =========================


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
    recognizer = sr.Recognizer()
    tts = pyttsx3.init()
    tts.setProperty("rate", 150)

    mic_index = find_best_microphone()
    mic = sr.Microphone(device_index=mic_index)

    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)

    while True:
        try:
            with mic as source:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)

            text = recognizer.recognize_google(audio, language="pl-PL").lower()

            print("VOICE:", text)

            if "start" in text:
                queue.put("start")
                tts.say("start")
                tts.runAndWait()

            elif "stop" in text:
                queue.put("stop")
                tts.say("stop")
                tts.runAndWait()

        except Exception:
            continue


# =========================
# VIDEO STREAM
# =========================


class VideoStream:
    def __init__(self, source):
        self.cap = cv2.VideoCapture(source)
        self.frame = None
        self.lock = threading.Lock()

        self.running = True
        self.playing = True

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


# =========================
# LIVE VIEW WIDGET
# =========================


class LiveView(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.ctrl = controller

        layout = QVBoxLayout(self)

        self.label = QLabel("LIVE VIEW")
        self.label.setAlignment(Qt.AlignCenter)

        self.video = VideoStream("video1.mp4")

        self.info = QLabel("Powiedz start / stop")
        self.info.setAlignment(Qt.AlignCenter)

        self.btn_back = QPushButton("Powrót")
        self.btn_back.clicked.connect(self.go_back)

        layout.addWidget(self.info)
        layout.addWidget(self.label)
        layout.addWidget(self.btn_back)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        self.queue = controller.queue

        self.queue_timer = QTimer()
        self.queue_timer.timeout.connect(self.check_queue)
        self.queue_timer.start(100)

    def update_frame(self):
        frame = self.video.get_frame()
        if frame is None:
            return

        frame = cv2.resize(frame, (640, 360))
        img = Image.fromarray(frame)

        qimg = ImageQt.ImageQt(img)
        pix = QPixmap.fromImage(qimg)

        self.label.setPixmap(pix)

    def check_queue(self):
        if self.queue:
            while not self.queue.empty():
                cmd = self.queue.get()

                if cmd == "start":
                    self.video.set_play(True)
                elif cmd == "stop":
                    self.video.set_play(False)

    def go_back(self):
        self.video.stop()
        self.ctrl.stop_voice()
        self.ctrl.show_menu()


# =========================
# FILE VIEW (3 STREAMS)
# =========================


class LoadFromFile(QWidget):
    def __init__(self, controller):
        super().__init__()

        self.ctrl = controller

        layout = QVBoxLayout(self)

        self.labels = QHBoxLayout()

        self.streams = [
            VideoStream("video1.mp4"),
            VideoStream("video2.mp4"),
            VideoStream("video3.mp4"),
        ]

        self.views = []

        for _ in range(3):
            lbl = QLabel()
            lbl.setAlignment(Qt.AlignCenter)
            self.views.append(lbl)
            self.labels.addWidget(lbl)

        self.btn_back = QPushButton("Powrót")
        self.btn_back.clicked.connect(self.go_back)

        layout.addLayout(self.labels)
        layout.addWidget(self.btn_back)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(30)

    def update(self):
        for i, s in enumerate(self.streams):
            frame = s.get_frame()
            if frame is None:
                continue

            frame = cv2.resize(frame, (320, 240))
            img = ImageQt.ImageQt(Image.fromarray(frame))
            pix = QPixmap.fromImage(img)

            self.views[i].setPixmap(pix)

    def go_back(self):
        for s in self.streams:
            s.stop()
        self.ctrl.show_menu()


# =========================
# MENU CONTROLLER
# =========================


class App(TemplateWindow):
    def __init__(self):
        super().__init__()

        self.queue = None
        self.voice_proc = None

        self.show_menu()

    def show_menu(self):
        # NIE tworzysz QWidget menu
        # tylko używasz lewego panelu TemplateWindow

        # najpierw czyścisz stare opcje (jeśli trzeba)
        for i in reversed(range(self.menu_layout.count())):
            widget = self.menu_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        self.add_menu_option("Dodaj na żywo", self.open_live)
        self.add_menu_option("Wczytaj z pliku", self.open_files)
        self.add_menu_option("Statystyki", lambda: None)
        self.add_menu_option("Progres", lambda: None)
        self.add_menu_option("Wyjście", self.close)

        # content reset
        placeholder = QWidget()
        self.set_content(placeholder)

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

    def open_live(self):
        self.start_voice()
        self.set_content(LiveView(self))

    def open_files(self):
        self.set_content(LoadFromFile(self))


# =========================
# RUN
# =========================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())
