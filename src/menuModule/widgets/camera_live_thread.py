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

        spoken_flags = {"prep": False, "sync_prompt": False, "start": False}
        last_voice_time = 0
        last_processed_rep_count = 0

        front_triggered = not self.has_front
        side_triggered = not self.has_side

        front_raised_frames = 0
        side_raised_frames = 0

        required_frames_hold = 15
        sync_timeout_seconds = 5.0
        first_trigger_time = None

        # Bufory opóźniające (FIFO)
        delay_buffer_f = []
        delay_buffer_s = []

        while self._is_running:
            has_f, frame_front = cap_front.read() if cap_front else (False, None)
            has_s, frame_side = cap_side.read() if cap_side else (False, None)

            display_front = frame_front.copy() if has_f else None
            display_side = frame_side.copy() if has_s else None

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

            elif self.current_state == self.STATE_VERIFY_SILHOUETTE:
                self.analyzer.queue_frames(frame_front, frame_side)
                self.analyzer.process_next_synced_step()
                info = self.analyzer.get_current_series_info()

                front_lost = (
                    (info["front_stage"] == "unknown") if self.has_front else False
                )
                side_lost = (
                    (info["side_stage"] == "unknown") if self.has_side else False
                )

                now = time.time()
                if front_lost and side_lost:
                    self.status_msg_updated.emit(
                        "⚠️ BŁĄD: Nie wykryto sylwetki! Stań przed kamerami."
                    )
                    if now - last_voice_time > 5.0:
                        self.voice.speak(
                            "Nie widzę cię w ogóle. Proszę, stań przed krzesłem."
                        )
                        last_voice_time = now
                elif front_lost or side_lost:
                    bad_cam = "PRZEDNIEJ" if front_lost else "BOCZNEJ"
                    self.status_msg_updated.emit(
                        f"⚠️ BŁĄD: Brak sylwetki w kamerze {bad_cam}! Odsuń ją."
                    )
                    if now - last_voice_time > 5.0:
                        self.voice.speak(
                            f"W kamerze {bad_cam.lower()} nie widać twojej pełnej sylwetki."
                        )
                        last_voice_time = now
                else:
                    if self.has_front and self.has_side:
                        self.current_state = self.STATE_SYNCHRONIZATION
                    else:
                        self.current_state = self.STATE_WORKOUT_ACTIVE

            elif self.current_state == self.STATE_SYNCHRONIZATION:
                self.status_msg_updated.emit(
                    "Synchronizacja: Przytrzymaj uniesioną dłoń nad głową..."
                )
                if not spoken_flags["sync_prompt"]:
                    self.voice.speak(
                        "Podnieś rękę wysoko nad głowę i przytrzymaj ją nieruchomo."
                    )
                    spoken_flags["sync_prompt"] = True

                # Analiza przodu za pomocą BEZSTANOWEJ funkcji
                if has_f:
                    if not front_triggered:
                        if self.analyzer.is_sync_gesture_detected(
                            frame_front, display_front, "front"
                        ):
                            front_raised_frames += 1
                            if front_raised_frames >= required_frames_hold:
                                front_triggered = True
                                self.voice.speak("Przód zsynchronizowany.")
                                if first_trigger_time is None:
                                    first_trigger_time = time.time()
                        else:
                            front_raised_frames = max(0, front_raised_frames - 1)

                        if front_raised_frames > 0 and display_front is not None:
                            cv.putText(
                                display_front,
                                f"Ladowanie... {front_raised_frames}/{required_frames_hold}",
                                (30, 50),
                                cv.FONT_HERSHEY_SIMPLEX,
                                1.0,
                                (0, 165, 255),
                                3,
                                cv.LINE_AA,
                            )

                    if front_triggered and not side_triggered:
                        delay_buffer_f.append(frame_front)
                        if display_front is not None:
                            cv.putText(
                                display_front,
                                "SYNCHRONIZACJA OK",
                                (30, 50),
                                cv.FONT_HERSHEY_SIMPLEX,
                                1.0,
                                (0, 255, 0),
                                3,
                                cv.LINE_AA,
                            )

                # Analiza boku za pomocą BEZSTANOWEJ funkcji
                if has_s:
                    if not side_triggered:
                        if self.analyzer.is_sync_gesture_detected(
                            frame_side, display_side, "side"
                        ):
                            side_raised_frames += 1
                            if side_raised_frames >= required_frames_hold:
                                side_triggered = True
                                self.voice.speak("Bok zsynchronizowany.")
                                if first_trigger_time is None:
                                    first_trigger_time = time.time()
                        else:
                            side_raised_frames = max(0, side_raised_frames - 1)

                        if side_raised_frames > 0 and display_side is not None:
                            cv.putText(
                                display_side,
                                f"Ladowanie... {side_raised_frames}/{required_frames_hold}",
                                (30, 50),
                                cv.FONT_HERSHEY_SIMPLEX,
                                1.0,
                                (0, 165, 255),
                                3,
                                cv.LINE_AA,
                            )

                    if side_triggered and not front_triggered:
                        delay_buffer_s.append(frame_side)
                        if display_side is not None:
                            cv.putText(
                                display_side,
                                "SYNCHRONIZACJA OK",
                                (30, 50),
                                cv.FONT_HERSHEY_SIMPLEX,
                                1.0,
                                (0, 255, 0),
                                3,
                                cv.LINE_AA,
                            )

                # Rygorystyczny TIMEOUT 5 sekund
                if first_trigger_time is not None and not (
                    front_triggered and side_triggered
                ):
                    if (time.time() - first_trigger_time) > sync_timeout_seconds:
                        self.status_msg_updated.emit(
                            "⚠️ BŁĄD: Przekroczono czas synchronizacji. Trening przerwany!"
                        )
                        self.voice.speak(
                            "Czas minął. Przerywam trening z powodu braku synchronizacji drugiej kamery."
                        )
                        self.stop()
                        return

                if front_triggered and side_triggered:
                    self.current_state = self.STATE_WORKOUT_ACTIVE

            elif self.current_state == self.STATE_WORKOUT_ACTIVE:
                if not spoken_flags["start"]:
                    self.voice.speak(
                        "Trening zsynchronizowany. Możesz rozpocząć serię dipów."
                    )
                    spoken_flags["start"] = True

                # Wyrównywanie opóźnienia z użyciem FIFO
                f_sync = frame_front
                s_sync = frame_side

                if self.has_front:
                    if delay_buffer_f:
                        delay_buffer_f.append(frame_front)
                        f_sync = delay_buffer_f.pop(0)
                    else:
                        f_sync = frame_front

                if self.has_side:
                    if delay_buffer_s:
                        delay_buffer_s.append(frame_side)
                        s_sync = delay_buffer_s.pop(0)
                    else:
                        s_sync = frame_side

                # Karmimy analizator zsynchronizowanymi klatkami
                self.analyzer.queue_frames(f_sync, s_sync)
                self.analyzer.process_next_synced_step()

                info = self.analyzer.get_current_series_info()

                # Twarde odcięcie w przypadku desynchronizacji analizatora
                if info.get("mismatch_detected", False):
                    self.status_msg_updated.emit(
                        "⚠️ BŁĄD: Klatki rozsynchronizowały się! (Desync)"
                    )
                    self.voice.speak(
                        "Trening przerwany ze względu na rozsynchronizowanie perspektyw."
                    )
                    self.stop()
                    return

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
                        errors_pool.append("Kontroluj rozstaw rąk na krześle.")
                    if not info["body_correct"]:
                        errors_pool.append(
                            "Kontroluj tempo ćwiczenia, nie spiesz się tak."
                        )

                    if not errors_pool:
                        self.voice.speak("Świetnie, idealne powtórzenie!")
                    else:
                        self.voice.speak(random.choice(errors_pool))

                # Podgląd AR na żywo - odbierany prosto z przetworzonego ułamka sekundy wewnątrz analizatora
                display_front = (
                    self.analyzer.get_agr_frame("front") if self.has_front else None
                )
                display_side = (
                    self.analyzer.get_agr_frame("side") if self.has_side else None
                )

            self.frame_processed.emit(display_front, display_side)
            time.sleep(0.033)

        if cap_front:
            cap_front.release()
        if cap_side:
            cap_side.release()

    def stop(self):
        self._is_running = False
        self.wait()
