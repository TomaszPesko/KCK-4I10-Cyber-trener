import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

# Importujemy stworzoną wcześniej bibliotekę (zgodnie z Twoją nazwą: menu.py)
from menu import AppWindow, Screen
from video_manager import VideoManager


class CyberTrener(AppWindow):
    """Główna klasa aplikacji zarządzająca strukturą ekranów oraz interfejsem

    komunikacji z przyszłymi modelami danych i logiką biznesową.
    """

    def __init__(self):
        # Inicjalizacja bazowego okna z biblioteki menu.py
        super().__init__(title="CyberTrener - Twój E-Trener AI")
        self.video_manager = VideoManager()
        self.camera_count = 1
        self.selected_perspective = "Przód"
        # Inicjalizacja struktury menu aplikacji
        self._inicjalizuj_ekrany()

        # Uruchomienie aplikacji od strony głównej
        self.switch_to_screen("strona_glowna")

    def _inicjalizuj_ekrany(self):
        """Tworzy i rejestruje wszystkie ekrany wewnątrz aplikacji."""
        # ----------------------------------------------------
        # 1. STRONA GŁÓWNA (Menu Główne)
        # ----------------------------------------------------
        sg_content = self._tworz_placeholder_zawartosci(
            "CyberTrener AI", "Witaj! Wybierz moduł aplikacji z menu po lewej."
        )
        self.screen_glowna = Screen(sg_content)
        self.screen_glowna.add_option(
            "Tworzenie serii", lambda: self.switch_to_screen("tworzenie_serii")
        )
        self.screen_glowna.add_option(
            "Wczytywanie serii", lambda: self.switch_to_screen("wczytywanie_serii")
        )
        self.screen_glowna.add_option(
            "Analiza postępów", lambda: self.switch_to_screen("analiza_postepow")
        )
        self.screen_glowna.add_option("Zamknij program", self.close)
        self.register_screen("strona_glowna", self.screen_glowna)

        # ----------------------------------------------------
        # 2. STRONA: TWORZENIE SERII
        # ----------------------------------------------------
        ts_content = self._tworz_placeholder_zawartosci(
            "Nowa Seria Treningowa",
            "Kamera gotowa. Wybierz perspektywę, aby rozpocząć analizę ruchu.",
        )
        self.screen_tworzenie = Screen(ts_content)
        self.screen_tworzenie.add_option("Start", self._start_nagrywania_akcja)
        self.screen_tworzenie.add_option(
            "1 kamera", lambda: self._ustaw_liczbe_kamer(1)
        )
        self.screen_tworzenie.add_option(
            "2 kamery", lambda: self._ustaw_liczbe_kamer(2)
        )
        self.screen_tworzenie.add_option(
            "Perspektywa z przodu", lambda: self._ustaw_perspektywe_akcja("Przód")
        )
        self.screen_tworzenie.add_option(
            "Perspektywa z boku", lambda: self._ustaw_perspektywe_akcja("Bok")
        )
        self.screen_tworzenie.add_option("Zapisz serię", self._zapisz_serie_akcja)
        self.screen_tworzenie.add_option(
            "Wróć", lambda: self.switch_to_screen("strona_glowna")
        )
        self.register_screen("tworzenie_serii", self.screen_tworzenie)

        # ----------------------------------------------------
        # 3. STRONA: WCZYTYWANIE SERII
        # ----------------------------------------------------
        ws_content = self._tworz_placeholder_zawartosci(
            "Archiwum Serii",
            "Wczytaj zapisany plik wideo z dysku lub bazy danych.",
        )
        self.screen_wczytywanie = Screen(ws_content)
        self.screen_wczytywanie.add_option(
            "Perspektywa z przodu", lambda: self._wczytaj_wideo_akcja("Przód")
        )
        self.screen_wczytywanie.add_option(
            "Perspektywa z boku", lambda: self._wczytaj_wideo_akcja("Bok")
        )
        self.screen_wczytywanie.add_option(
            "Zapisz serię",
            lambda: print("[Model] Zapisywanie zmian w wczytanej serii..."),
        )
        self.screen_wczytywanie.add_option(
            "Wróć", lambda: self.switch_to_screen("strona_glowna")
        )
        self.register_screen("wczytywanie_serii", self.screen_wczytywanie)

        # ----------------------------------------------------
        # 4. STRONA: ANALIZA POSTĘPÓW
        # ----------------------------------------------------
        ap_content = self._tworz_placeholder_zawartosci(
            "Centrum Statystyk", "Wczytaj dane treningowe, aby zobaczyć wykresy."
        )
        self.screen_analiza = Screen(ap_content)
        self.screen_analiza.add_option(
            "Wczytaj dane treningowe", self._wczytaj_dane_treningowe_akcja
        )
        self.screen_analiza.add_option(
            "Jakość serii", lambda: self._pokaz_statystyke_akcja("Jakość serii (%)")
        )
        self.screen_analiza.add_option(
            "Ilość powtórzeń",
            lambda: self._pokaz_statystyke_akcja("Liczba powtórzeń"),
        )
        self.screen_analiza.add_option(
            "Czas trwania serii",
            lambda: self._pokaz_statystyke_akcja("Czas trwania (s)"),
        )
        self.screen_analiza.add_option(
            "Liczba serii w ciągu dnia",
            lambda: self._pokaz_statystyke_akcja("Suma serii per dzień"),
        )
        self.screen_analiza.add_option(
            "Wróć", lambda: self.switch_to_screen("strona_glowna")
        )
        self.register_screen("analiza_postepow", self.screen_analiza)

    # ===== INTERFEJS DLA PRZYSZŁYCH MODELI I AKCJI =====
    # W tych metodach w przyszłości wepniesz wywołania do swoich klas logicznych/baz danych.
    def _ustaw_liczbe_kamer(self, liczba):
        self.camera_count = liczba
        print(f"[Kamera] Wybrano konfigurację: {liczba} kamera(y)")

    def _start_nagrywania_akcja(self):

        print(f"[Konfiguracja] Liczba kamer: {self.camera_count}")

        if self.camera_count == 1:
            print(
                f"[Konfiguracja] Perspektywa: {self.selected_perspective}"
            )
        else:
            print(
                "[Konfiguracja] Przód - laptop, Bok - telefon"
            )

        if self.camera_count == 1:

            connected = self.video_manager.connect_single_camera(0)

            if connected:
                print("[Kamera] Kamera została podłączona")
            else:
                print("[Kamera] Nie udało się połączyć z kamerą")

        else:

            connected = self.video_manager.connect_dual_cameras(0, 1)

            if connected:
                print("[Kamera] Kamera przednia została podłączona")
                print("[Kamera] Kamera boczna została podłączona")
            else:
                print("[Kamera] Nie udało się uruchomić dwóch kamer")

    def _ustaw_perspektywe_akcja(self, perspektywa: str):
        self.selected_perspective = perspektywa
        print(
            f"[Model AI] Wybrano perspektywę: {perspektywa}"
        )

    def _zapisz_serie_akcja(self):
        print("[Baza Danych] Zapisywanie nowej serii do historii treningów...")

    def _wczytaj_wideo_akcja(self, perspektywa: str):
        print(f"[Pliki] Otwieranie eksploratora plików dla perspektywy: {perspektywa}")

    def _wczytaj_dane_treningowe_akcja(self):
        print("[Baza Danych] Pobieranie historycznych punktów danych...")

    def _pokaz_statystyke_akcja(self, typ_statystyki: str):
        print(f"[Wykres] Generowanie i podmiana widoku dla: {typ_statystyki}")

    # ===== POMOCNICZE =====

    def _tworz_placeholder_zawartosci(self, tytul: str, podtytul: str) -> QWidget:
        """Generuje tymczasowy widżet tekstowy po prawej stronie,

        który w przyszłości zastąpisz wykresem lub odtwarzaczem wideo.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)

        lbl_tytul = QLabel(tytul)
        lbl_tytul.setStyleSheet(
            "color: #00cc66; font-size: 28px; font-weight: bold; margin-bottom: 10px;"
        )
        lbl_tytul.setAlignment(Qt.AlignCenter)

        lbl_podtytul = QLabel(podtytul)
        lbl_podtytul.setStyleSheet("color: #dddddd; font-size: 16px;")
        lbl_podtytul.setAlignment(Qt.AlignCenter)

        layout.addWidget(lbl_tytul)
        layout.addWidget(lbl_podtytul)
        return widget


# ===== URUCHOMIENIE APLIKACJI =====

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CyberTrener()
    window.show()
    sys.exit(app.exec())
