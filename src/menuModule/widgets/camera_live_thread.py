import random
import time

import cv2 as cv
from PySide6.QtCore import QThread, Signal

from src.videoAnalysisModule.VideoAnalyzer import VideoAnalyzer
from src.voiceSynthesisModule.VoiceSynthesizer import VoiceSynthesizer


class CameraLiveThread(QThread):
    frame_processed = Signal(object, object)
    status_msg_updated = Signal(str)

    def __init__(
        self,
        shared_analyzer: VideoAnalyzer,
        front_index=0,
        side_index=1,
        has_front=True,
        has_side=True,
    ):
        super().__init__()
        self.analyzer = shared_analyzer
        self.front_index = front_index
        self.side_index = side_index
        self.has_front = has_front
        self.has_side = has_side
        self._is_running = True
        self.voice = VoiceSynthesizer()

        self.STATE_PREPARATION = "PREPARATION"
        self.STATE_VERIFY_SILHOUETTE = "VERIFY_SILHOUETTE"
        self.STATE_SYNCHRONIZATION = "SYNCHRONIZATION"
        self.STATE_WORKOUT_ACTIVE = "WORKOUT_ACTIVE"
        self.current_state = self.STATE_PREPARATION

    def run(self):
        cap_front = cv.VideoCapture(self.front_index) if self.has_front else None
        cap_side = cv.VideoCapture(self.side_index) if self.has_side else None

        self.analyzer.reset()
        state_start_time = time.time()

        spoken_flags = {
            "prep": False,
            "silh_error": False,
            "silh_none": False,
            "sync_prompt": False,
            "start": False,
        }
        last_voice_time = 0

        # Kolejki synchronizacyjne na klatki wideo w celu niwelowania różnic w latencji
        front_buffer = []
        side_buffer = []

        front_triggered = not self.has_front
        side_triggered = not self.has_side
        last_processed_rep_count = 0

        while self._is_running:
            has_f, frame_front = cap_front.read() if cap_front else (False, None)
            has_s, frame_side = cap_side.read() if cap_side else (False, None)

            display_front = frame_front.copy() if has_f else None
            display_side = frame_side.copy() if has_s else None

            # --- STAN 1: PODEJŚCIE DO KRZESŁA (3 SEKUNDY) ---
            if self.current_state == self.STATE_PREPARATION:
                elapsed = time.time() - state_start_time
                self.status_msg_updated.emit(
                    f"Przygotuj się! Podejdź do krzesła... {max(0, int(4 - elapsed))}s"
                )
                if not spoken_flags["prep"]:
                    self.voice.speak(
                        "Cześć! Przygotuj się do ćwiczenia. Podejdź do krzesła, trening rozpocznie się za trzy sekundy."
                    )
                    spoken_flags["prep"] = True
                if elapsed >= 3.0:
                    self.current_state = self.STATE_VERIFY_SILHOUETTE

            # --- STAN 2: WERYFIKACJA SYLWETKI ---
            elif self.current_state == self.STATE_VERIFY_SILHOUETTE:
                self.analyzer.queue_frames(frame_front, frame_side)
                self.analyzer.process_next_synced_step()
                info = self.analyzer.get_current_series_info()

                # Sprawdzamy, czy sylwetka została zgubiona (zwraca "unknown")
                front_lost = (
                    (info["front_stage"] == "unknown") if self.has_front else False
                )
                side_lost = (
                    (info["side_stage"] == "unknown") if self.has_side else False
                )

                now = time.time()
                if front_lost and side_lost:
                    self.status_msg_updated.emit(
                        "⚠️ BŁĄD: Nie wykryto żadnej sylwetki! Stań w polu widzenia kamer."
                    )
                    if now - last_voice_time > 5.0:
                        self.voice.speak(
                            "Nie widzę cię w ogóle. Proszę, stań przed krzesłem w polu widzenia kamer."
                        )
                        last_voice_time = now
                elif front_lost or side_lost:
                    bad_cam = "PRZEDNIEJ" if front_lost else "BOCZNEJ"
                    self.status_msg_updated.emit(
                        f"⚠️ BŁĄD: Brak pełnej sylwetki w kamerze {bad_cam}! Odsuń urządzenie."
                    )
                    if now - last_voice_time > 5.0:
                        self.voice.speak(
                            f"W kamerze {bad_cam.lower()} nie widać twojej pełnej sylwetki. Proszę, odsuń ją nieco."
                        )
                        last_voice_time = now
                else:
                    # Sylwetki są kompletne w obu strumieniach -> Przejdź do synchronizacji lub ćwiczenia
                    if self.has_front and self.has_side:
                        self.current_state = self.STATE_SYNCHRONIZATION
                    else:
                        self.current_state = self.STATE_WORKOUT_ACTIVE

            # --- STAN 3: SYNCHRONIZACJA LATENCJI STRUMIENI (IGNOROWANIE + KOLEJKOWANIE) ---
            elif self.current_state == self.STATE_SYNCHRONIZATION:
                self.status_msg_updated.emit(
                    "Synchronizacja latencji kamer... Unieś dłoń nad głowę!"
                )
                if not spoken_flags["sync_prompt"]:
                    self.voice.speak(
                        "Wykryto dwie perspektywy. Aby zsynchronizować kamery, unieś teraz jedną dłoń wysoko nad głowę."
                    )
                    spoken_flags["sync_prompt"] = True

                # Dopóki dana kamera nie zarejestruje uniesienia dłoni, ignorujemy klatki na wykresach powtórzeń,
                # ale zbieramy je do buforów w celu późniejszego wyrównania.
                if has_f:
                    self.analyzer.queue_frames(front_frame=frame_front)
                    self.analyzer._analyze_perspective(frame_front, "front")
                    if not front_triggered:
                        if self.analyzer.is_hand_raised_front():
                            front_triggered = True
                            self.voice.speak("Kamera z przodu zsynchronizowana.")
                        else:
                            # Ignorujemy – nie dodajemy do bufora przetwarzania dopóki nie ma impulsu startu
                            pass
                    if front_triggered:
                        front_buffer.append(frame_front)

                if has_s:
                    self.analyzer.queue_frames(side_frame=frame_side)
                    self.analyzer._analyze_perspective(frame_side, "side")
                    if not side_triggered:
                        if self.analyzer.is_hand_raised_side():
                            side_triggered = True
                            self.voice.speak("Kamera z boku zsynchronizowana.")
                        else:
                            pass
                    if side_triggered:
                        side_buffer.append(frame_side)

                # Jeżeli obie kamery zarejestrowały punkt odniesienia, opróżniamy bufory klatka po klatce
                if front_triggered and side_triggered:
                    while front_buffer and side_buffer:
                        self.analyzer.queue_frames(
                            front_buffer.pop(0), side_buffer.pop(0)
                        )
                        self.analyzer.process_next_synced_step()

                    self.current_state = self.STATE_WORKOUT_ACTIVE

            # --- STAN 4: AKTYWNY TRENING ---
            elif self.current_state == self.STATE_WORKOUT_ACTIVE:
                if not spoken_flags["start"]:
                    self.voice.speak(
                        "Synchronizacja zakończona. Obie kamery są wyrównane. Możesz rozpocząć serię dipów!"
                    )
                    spoken_flags["start"] = True

                self.analyzer.queue_frames(frame_front, frame_side)
                self.analyzer.process_next_synced_step()

                info = self.analyzer.get_current_series_info()
                self.status_msg_updated.emit(
                    f"Trening aktywny! Liczba powtórzeń: {info['total_reps']}"
                )

                if info["total_reps"] > last_processed_rep_count:
                    last_processed_rep_count = info["total_reps"]

                    errors_pool = []
                    if not info["leg_correct"]:
                        errors_pool.append(
                            "Zejdź głębiej, robisz za płytkie powtórzenia."
                        )
                    if info["hand_feedback"] != "OK":
                        if info["hand_feedback"] == "Too narrow":
                            errors_pool.append("Trzymaj ręce nieco szerzej na krześle.")
                        else:
                            errors_pool.append(
                                "Trzymaj ręce bliżej krzesła, rozstawiasz je za szeroko."
                            )
                    if not info["body_correct"]:
                        errors_pool.append(
                            "Kontroluj tempo ćwiczenia, nie spiesz się tak."
                        )

                    if not errors_pool:
                        self.voice.speak("Świetnie, idealne powtórzenie!")
                    else:
                        # Dokładnie jeden losowy komunikat przy wielu błędach naraz
                        self.voice.speak(random.choice(errors_pool))

            self.frame_processed.emit(display_front, display_side)
            time.sleep(0.033)

        if cap_front:
            cap_front.release()
        if cap_side:
            cap_side.release()

    def stop(self):
        self._is_running = False
        self.wait()
