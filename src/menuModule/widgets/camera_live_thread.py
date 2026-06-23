import random
import time

import cv2 as cv
from PySide6.QtCore import QThread, Signal

from src.videoAnalysisModule.VideoAnalyzer import VideoAnalyzer
from src.voiceSynthesisModule.VoiceSynthesizer import VoiceSynthesizer


class CameraLiveThread(QThread):
    frame_processed = Signal(object, object)
    status_msg_updated = Signal(str)

    # --- STAŁE KONFIGURACYJNE ---
    REQUIRED_FRAMES_HOLD = 15  # 0.5s przy 30fps
    SYNC_TIMEOUT_SECONDS = 5.0
    PREP_TIME_SECONDS = 3.0
    VOICE_COOLDOWN_SECONDS = 5.0

    # --- STANY ---
    STATE_PREPARATION = "PREPARATION"
    STATE_VERIFY_SILHOUETTE = "VERIFY_SILHOUETTE"
    STATE_SYNCHRONIZATION = "SYNCHRONIZATION"
    STATE_WORKOUT_ACTIVE = "WORKOUT_ACTIVE"

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

        self._reset_internal_variables()

    def _reset_internal_variables(self):
        self.current_state = self.STATE_PREPARATION
        self.state_start_time = time.time()
        self.first_trigger_time = None

        self.spoken_flags = {"prep": False, "sync_prompt": False, "start": False}
        self.last_voice_time = 0
        self.last_processed_rep_count = 0

        self.front_triggered = not self.has_front
        self.side_triggered = not self.has_side

        self.front_raised_frames = 0
        self.side_raised_frames = 0
        self.end_gesture_frames = 0

        self.delay_buffer_f = []
        self.delay_buffer_s = []

    def run(self):
        cap_front = cv.VideoCapture(self.front_index) if self.has_front else None
        cap_side = cv.VideoCapture(self.side_index) if self.has_side else None

        self.analyzer.reset()
        self._reset_internal_variables()

        while self._is_running:
            has_f, frame_front = cap_front.read() if cap_front else (False, None)
            has_s, frame_side = cap_side.read() if cap_side else (False, None)

            display_front = frame_front.copy() if has_f else None
            display_side = frame_side.copy() if has_s else None

            if self.current_state == self.STATE_PREPARATION:
                display_front, display_side = self._handle_preparation(
                    display_front, display_side
                )
                self.front_raised_frames = 0
                self.side_raised_frames = 0

            elif self.current_state == self.STATE_VERIFY_SILHOUETTE:
                display_front, display_side = self._handle_verification(
                    frame_front, frame_side, display_front, display_side
                )

            elif self.current_state == self.STATE_SYNCHRONIZATION:
                display_front, display_side = self._handle_synchronization(
                    frame_front,
                    frame_side,
                    display_front,
                    display_side,
                    cap_front,
                    cap_side,
                )

            elif self.current_state == self.STATE_WORKOUT_ACTIVE:
                display_front, display_side = self._handle_workout(
                    frame_front, frame_side, has_f, has_s
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

    def _handle_preparation(self, display_front, display_side):
        elapsed = time.time() - self.state_start_time
        countdown = max(0, int((self.PREP_TIME_SECONDS + 1) - elapsed))
        self.status_msg_updated.emit(f"Zajmij pozycję na krześle... {countdown}s")

        if not self.spoken_flags["prep"]:
            self.voice.speak("prep_start")
            self.spoken_flags["prep"] = True

        if elapsed >= self.PREP_TIME_SECONDS:
            self.current_state = self.STATE_VERIFY_SILHOUETTE

        return display_front, display_side

    def _handle_verification(
        self, frame_front, frame_side, display_front, display_side
    ):
        self.analyzer.queue_frames(frame_front, frame_side)
        self.analyzer.process_next_synced_step()
        info = self.analyzer.get_current_series_info()

        front_lost = (info["front_stage"] == "unknown") if self.has_front else False
        side_lost = (info["side_stage"] == "unknown") if self.has_side else False

        now = time.time()
        if front_lost and side_lost:
            self.status_msg_updated.emit("⚠️ BŁĄD: Nie jesteś w kadrze!")
            if now - self.last_voice_time > self.VOICE_COOLDOWN_SECONDS:
                self.voice.speak("sil_lost_all")
                self.last_voice_time = now
        elif front_lost or side_lost:
            bad_cam = "PRZEDNIEJ" if front_lost else "BOCZNEJ"
            self.status_msg_updated.emit(f"⚠️ BŁĄD: Brak sylwetki w kamerze {bad_cam}!")
            if now - self.last_voice_time > self.VOICE_COOLDOWN_SECONDS:
                key = "sil_lost_front" if front_lost else "sil_lost_side"
                self.voice.speak(key)
                self.last_voice_time = now
        else:
            self.current_state = self.STATE_SYNCHRONIZATION

        return display_front, display_side

    def _handle_synchronization(
        self, frame_front, frame_side, display_front, display_side, cap_front, cap_side
    ):
        self.status_msg_updated.emit("Podnieś dłoń, aby zameldować gotowość...")

        if not self.spoken_flags["sync_prompt"]:
            self.voice.speak("sync_prompt")
            self.spoken_flags["sync_prompt"] = True

        if self.has_front:
            if not self.front_triggered:
                if self.analyzer.is_sync_gesture_detected(
                    frame_front, display_front, "front"
                ):
                    self.front_raised_frames += 1
                    if self.front_raised_frames >= self.REQUIRED_FRAMES_HOLD:
                        self.front_triggered = True
                        msg_key = "sync_front_ok" if self.has_side else "sync_all_ok"
                        self.voice.speak(msg_key)
                        if self.first_trigger_time is None:
                            self.first_trigger_time = time.time()
                else:
                    self.front_raised_frames = max(0, self.front_raised_frames - 1)

                if self.front_raised_frames > 0 and display_front is not None:
                    self._draw_text(
                        display_front,
                        f"Gotowosc... {self.front_raised_frames}/{self.REQUIRED_FRAMES_HOLD}",
                        (0, 165, 255),
                    )

            if self.front_triggered and not self.side_triggered:
                self.delay_buffer_f.append(frame_front)
                if display_front is not None:
                    self._draw_text(display_front, "GOTOWY", (0, 255, 0))

        if self.has_side:
            if not self.side_triggered:
                if self.analyzer.is_sync_gesture_detected(
                    frame_side, display_side, "side"
                ):
                    self.side_raised_frames += 1
                    if self.side_raised_frames >= self.REQUIRED_FRAMES_HOLD:
                        self.side_triggered = True
                        msg_key = "sync_side_ok" if self.has_front else "sync_all_ok"
                        self.voice.speak(msg_key)
                        if self.first_trigger_time is None:
                            self.first_trigger_time = time.time()
                else:
                    self.side_raised_frames = max(0, self.side_raised_frames - 1)

                if self.side_raised_frames > 0 and display_side is not None:
                    self._draw_text(
                        display_side,
                        f"Gotowosc... {self.side_raised_frames}/{self.REQUIRED_FRAMES_HOLD}",
                        (0, 165, 255),
                    )

            if self.side_triggered and not self.front_triggered:
                self.delay_buffer_s.append(frame_side)
                if display_side is not None:
                    self._draw_text(display_side, "GOTOWY", (0, 255, 0))

        if self.first_trigger_time is not None and not (
            self.front_triggered and self.side_triggered
        ):
            if (time.time() - self.first_trigger_time) > self.SYNC_TIMEOUT_SECONDS:
                self.status_msg_updated.emit(
                    "⚠️ Anulowano z powodu braku potwierdzenia w drugiej kamerze."
                )
                self.voice.speak("sync_timeout")
                self.stop()
                return display_front, display_side

        if self.front_triggered and self.side_triggered:
            self.current_state = self.STATE_WORKOUT_ACTIVE

        return display_front, display_side

    def _handle_workout(self, frame_front, frame_side, has_f, has_s):
        if not self.spoken_flags["start"]:
            self.voice.speak("workout_start")
            self.spoken_flags["start"] = True

        # --- WYKRYWANIE GESTU ZAKOŃCZENIA SERII ---
        end_detected = False
        if has_f and frame_front is not None:
            if self.analyzer.is_sync_gesture_detected(frame_front, perspective="front"):
                end_detected = True

        if has_s and frame_side is not None:
            if self.analyzer.is_sync_gesture_detected(frame_side, perspective="side"):
                end_detected = True

        if end_detected:
            self.end_gesture_frames += 1
            if self.end_gesture_frames >= self.REQUIRED_FRAMES_HOLD:
                self.status_msg_updated.emit("Trening przerwany / ukończony gestem.")
                self.voice.speak("workout_end")
                self.stop()
                return None, None
        else:
            self.end_gesture_frames = max(0, self.end_gesture_frames - 1)

        f_sync = frame_front
        s_sync = frame_side

        if self.has_front:
            if self.delay_buffer_f:
                self.delay_buffer_f.append(frame_front)
                f_sync = self.delay_buffer_f.pop(0)
            else:
                f_sync = frame_front

        if self.has_side:
            if self.delay_buffer_s:
                self.delay_buffer_s.append(frame_side)
                s_sync = self.delay_buffer_s.pop(0)
            else:
                s_sync = frame_side

        self.analyzer.queue_frames(f_sync, s_sync)
        self.analyzer.process_next_synced_step()
        info = self.analyzer.get_current_series_info()

        if info.get("mismatch_detected", False):
            self.status_msg_updated.emit("⚠️ BŁĄD: Klatki z kamer się rozjechały!")
            self.voice.speak("error_desync")
            self.stop()
            return None, None

        self.status_msg_updated.emit(
            f"Aktywny set! Reps: {info['total_reps']} (Podnieś rękę, aby zakończyć)"
        )

        if info["total_reps"] > self.last_processed_rep_count:
            self.last_processed_rep_count = info["total_reps"]
            errors_pool = []

            if not info["leg_correct"]:
                errors_pool.append("err_shallow")
            if info["hand_feedback"] != "OK":
                errors_pool.append("err_width")
            if not info["body_correct"]:
                errors_pool.append("err_tempo")

            if not errors_pool:
                self.voice.speak("rep_perfect")
            else:
                self.voice.speak(random.choice(errors_pool))

        display_front = self.analyzer.get_agr_frame("front") if has_f else None
        display_side = self.analyzer.get_agr_frame("side") if has_s else None

        if self.end_gesture_frames > 0:
            if display_front is not None:
                self._draw_text(
                    display_front,
                    f"Zamykanie... {self.end_gesture_frames}/{self.REQUIRED_FRAMES_HOLD}",
                    (0, 0, 255),
                )
            if display_side is not None:
                self._draw_text(
                    display_side,
                    f"Zamykanie... {self.end_gesture_frames}/{self.REQUIRED_FRAMES_HOLD}",
                    (0, 0, 255),
                )

        return display_front, display_side

    def _draw_text(self, frame, text, color):
        cv.putText(
            frame, text, (30, 50), cv.FONT_HERSHEY_SIMPLEX, 1.0, color, 3, cv.LINE_AA
        )
