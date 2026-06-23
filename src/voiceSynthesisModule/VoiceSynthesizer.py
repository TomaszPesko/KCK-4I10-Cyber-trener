import os
import queue
import threading
import time


class VoiceSynthesizer:
    def __init__(self):
        self.speech_queue = queue.Queue()

        # Nowa ścieżka do nagrań audio w głównym katalogu projektu
        self.sound_dir = os.path.join(os.getcwd(), "resources", "sound")
        os.makedirs(self.sound_dir, exist_ok=True)

        threading.Thread(target=self._speech_worker_loop, daemon=True).start()

    def speak(self, sound_key: str):
        """Wrzuca klucz nagrania do bezpiecznej kolejki FIFO."""
        if sound_key:
            self.speech_queue.put(sound_key)

    def _speech_worker_loop(self):
        while True:
            sound_key = self.speech_queue.get()
            if sound_key is None:
                break

            try:
                # Szukamy pliku mp3, a w ramach fallbacku wav
                filename = os.path.join(self.sound_dir, f"{sound_key}.mp3")
                if not os.path.exists(filename):
                    filename = os.path.join(self.sound_dir, f"{sound_key}.wav")

                if os.path.exists(filename) and os.path.getsize(filename) > 0:
                    self._play_file_via_pygame(filename)
                else:
                    print(
                        f"[VoiceSynthesizer] BŁĄD: Brak pliku dla komunikatu '{sound_key}'. Oczekiwano: {filename}"
                    )

            except Exception as e:
                print(f"[VoiceSynthesizer Error] Wystąpił błąd w workerze: {e}")

            finally:
                self.speech_queue.task_done()

    def _play_file_via_pygame(self, filename: str):
        """Odtwarzanie plików audio z użyciem PyGame."""
        try:
            import pygame

            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(44100, -16, 2, 512)
                pygame.mixer.init()

            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()

            # Czekamy, aż plik skończy się odtwarzać
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)

            pygame.mixer.music.unload()

        except Exception as e:
            print(f"[Pygame Audio Error] Nie udało się odtworzyć pliku {filename}: {e}")
