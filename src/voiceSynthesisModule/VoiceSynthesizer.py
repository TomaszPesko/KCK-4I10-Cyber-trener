import os
import queue
import sys
import threading
import time


class VoiceSynthesizer:
    def __init__(self):
        self.speech_queue = queue.Queue()
        self.cache_dir = "voice_cache"
        os.makedirs(self.cache_dir, exist_ok=True)

        self.force_offline = False

        threading.Thread(target=self._speech_worker_loop, daemon=True).start()

    def speak(self, text: str):
        """Metoda błyskawiczna: wrzuca tekst do bezpiecznej kolejki FIFO i wraca do wideo."""
        if text:
            print(f"[VoiceSynthesizer Queue] Dodano komunikat: {text}")
            self.speech_queue.put(text)

    def _speech_worker_loop(self):
        while True:
            text = self.speech_queue.get()
            if text is None:
                break

            try:
                # Usuwamy lub komentujemy linię "if self.force_offline:"
                filename = f"{self.cache_dir}/msg_{abs(hash(text))}.mp3"

                if not os.path.exists(filename) or os.path.getsize(filename) == 0:
                    import asyncio

                    import edge_tts

                    async def download():
                        communicate = edge_tts.Communicate(text, "pl-PL-MarekNeural")
                        await communicate.save(filename)

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    # Zwiększamy timeout do 3 sekund, na wypadek wolniejszego internetu
                    loop.run_until_complete(asyncio.wait_for(download(), timeout=3.0))
                    loop.close()

                if os.path.exists(filename) and os.path.getsize(filename) > 0:
                    self._play_file_via_pygame(filename)
                else:
                    raise Exception("Pusty plik cache")

            except Exception as e:
                print(
                    f"[Voice Synthesizer Warning] Chmura jeszcze zablokowana, używam offline: {e}"
                )
                self._play_offline_fallback(text)
            finally:
                self.speech_queue.task_done()

    def _play_file_via_pygame(self, filename: str):
        """Odtwarzanie plików MP3 z obsługą wyjątków audio."""
        try:
            import pygame

            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(44100, -16, 2, 512)
                pygame.mixer.init()

            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
            pygame.mixer.music.unload()
        except Exception as e:
            print(f"[Pygame Audio Error] Nie udało się odtworzyć pliku {filename}: {e}")

    def _play_offline_fallback(self, text: str):
        """Natywny, błyskawiczny syntezator systemowy, który działa bez internetu."""
        try:
            import platform

            current_os = platform.system()

            if current_os == "Linux":
                # spd-say to standard w Ubuntu/Debianie, wywołanie w tle (&) nie blokuje procesu
                os.system(f'spd-say -l pl "{text}" || espeak -v pl "{text}" &')
            elif current_os == "Windows":
                ps_command = f'Add-Type -AssemblyName System.speech; $val = New-Object System.Speech.Synthesis.SpeechSynthesizer; $val.Speak("{text}")'
                os.system(f'powershell -Command "{ps_command}" &')
            elif current_os == "Darwin":
                os.system(f'say -v Zosia "{text}" &')
        except Exception as fallback_error:
            print(
                f"[Fatal TTS Fallback Error] Wszystkie systemy mowy zawiodły: {fallback_error}"
            )
