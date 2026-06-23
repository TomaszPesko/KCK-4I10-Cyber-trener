# ==> src/voiceSynthesisModule/VoiceSynthesizer.py <==
import os
import queue
import threading
import time


class VoiceSynthesizer:
    def __init__(self):
        self.speech_queue = queue.Queue()

        # Definicja ścieżki do lokalnych zasobów dźwiękowych w katalogu głównym projektu
        self.sound_dir = os.path.join(os.getcwd(), "resources", "sound")
        os.makedirs(self.sound_dir, exist_ok=True)

        threading.Thread(target=self._speech_worker_loop, daemon=True).start()

    def speak(self, sound_key: str):
        """Wrzuca klucz pliku audio do bezpiecznej kolejki i natychmiast uwalnia wątek wideo."""
        if sound_key:
            self.speech_queue.put(sound_key)

    def play_hover_sound(self):
        """Metoda dedykowana do wywołania natychmiastowego dźwięku hover w menu (poza kolejką)."""
        filename = os.path.join(self.sound_dir, "menu_hover.mp3")
        if not os.path.exists(filename):
            filename = os.path.join(self.sound_dir, "menu_hover.wav")

        if os.path.exists(filename):
            threading.Thread(
                target=self._play_direct, args=(filename,), daemon=True
            ).start()

    def _speech_worker_loop(self):
        while True:
            sound_key = self.speech_queue.get()
            if sound_key is None:
                break

            try:
                # Wsparcie dla formatów MP3 oraz WAV
                filename = os.path.join(self.sound_dir, f"{sound_key}.mp3")
                if not os.path.exists(filename):
                    filename = os.path.join(self.sound_dir, f"{sound_key}.wav")

                if os.path.exists(filename) and os.path.getsize(filename) > 0:
                    self._play_file_via_pygame(filename)
                else:
                    print(
                        f"[CyberTrainer Audio Warning] Brak nagrania dla komendy '{sound_key}' w folderze {self.sound_dir}"
                    )
            except Exception as e:
                print(f"[Audio Worker Error] Problem z odtwarzaniem: {e}")
            finally:
                self.speech_queue.task_done()

    def _play_file_via_pygame(self, filename: str):
        try:
            import pygame

            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(44100, -16, 2, 512)
                pygame.mixer.init()

            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.02)
            pygame.mixer.music.unload()
        except Exception as e:
            print(f"[Pygame Audio Mixer Error] Plik {filename}: {e}")

    def _play_direct(self, filename: str):
        """Szybkie odtwarzanie efektów UI za pomocą niezależnego Sound-Channela, by nie blokować muzyki trenera."""
        try:
            import pygame

            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(44100, -16, 2, 512)
                pygame.mixer.init()
            sound = pygame.mixer.Sound(filename)
            sound.play()
        except Exception:
            pass
