from datetime import datetime

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.include.set_data import WorkoutSet
from src.menuModule.date_dialog import DateTimeDialog
from src.menuModule.manual_set_widget import (
    DurationDialog,
    ManualPreviewWidget,
    RepetitionDialog,
    TrainingDataHistoryWidget,
)
from src.menuModule.menu import Screen
from src.menuModule.video_player import VideoAnalysisThread, VideoDisplayWidget


class BaseScreen(Screen):
    """Pomocnicza klasa bazowa ułatwiająca tworzenie powtarzalnych layoutów."""

    def __init__(self, title: str, subtitle: str):
        self.container = QWidget()
        layout = QVBoxLayout(self.container)
        layout.setAlignment(Qt.AlignCenter)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(
            "color: #00cc66; font-size: 28px; font-weight: bold; margin-bottom: 10px;"
        )
        lbl_title.setAlignment(Qt.AlignCenter)

        lbl_sub = QLabel(subtitle)
        lbl_sub.setStyleSheet("color: #dddddd; font-size: 16px;")
        lbl_sub.setAlignment(Qt.AlignCenter)

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_sub)
        super().__init__(self.container)


class MainScreen(BaseScreen):
    def __init__(self, navigator_cb):
        super().__init__("CyberTrener AI", "Witaj! Wybierz moduł z menu po lewej.")
        self.add_option("Tworzenie serii", lambda: navigator_cb("create_set"))
        self.add_option("Wczytywanie serii", lambda: navigator_cb("load_set"))
        self.add_option("Analiza postępów", lambda: navigator_cb("analyze_progress"))
        self.add_option("Zamknij program", lambda: navigator_cb("close"))


class CreateSetScreen(BaseScreen):
    def __init__(self, navigator_cb):
        super().__init__(
            "Nowa Seria Treningowa", "Wybierz sposób zapisu lub perspektywę AI."
        )
        self.add_option("Start", lambda: print("[Camera] Starting stream..."))
        self.add_option(
            "Perspektywa z przodu", lambda: print("[AI Model] Perspective: Front")
        )
        self.add_option(
            "Perspektywa z boku", lambda: print("[AI Model] Perspective: Side")
        )
        self.add_option(
            "Zdefiniuj Serię Ręcznie", lambda: navigator_cb("manual_definition")
        )
        self.add_option("Zapisz serię", lambda: print("[Database] Auto-saving set..."))
        self.add_option("Wróć", lambda: navigator_cb("main_page"))


class LoadSetScreen(Screen):
    def __init__(self, navigator_cb):
        # Główny kontener po prawej stronie
        self.main_container = QWidget()
        main_layout = QVBoxLayout(self.main_container)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # -------------------------------------------------------------
        # WIDGETY WYŚWIETLANIA (Przełącznik: Widok Statystyk / Odtwarzacz AR)
        # -------------------------------------------------------------
        self.display_stack = QStackedWidget()
        main_layout.addWidget(self.display_stack)

        # Widok 1: Tekstowe statystyki serii
        self.stats_view = QWidget()
        stats_layout = QVBoxLayout(self.stats_view)
        stats_layout.setAlignment(Qt.AlignCenter)

        self.lbl_stats_title = QLabel("Podgląd Wczytanej Serii Treningowej")
        self.lbl_stats_title.setStyleSheet(
            "color: #00cc66; font-size: 24px; font-weight: bold; margin-bottom: 15px;"
        )

        self.lbl_stats_content = QLabel(
            "Wybierz pliki wideo z menu po lewej stronie, aby rozpocząć."
        )
        self.lbl_stats_content.setStyleSheet(
            "color: #dddddd; font-size: 16px; line-height: 160%;"
        )
        self.lbl_stats_content.setAlignment(Qt.AlignCenter)

        stats_layout.addWidget(self.lbl_stats_title, alignment=Qt.AlignCenter)
        stats_layout.addWidget(self.lbl_stats_content, alignment=Qt.AlignCenter)
        self.display_stack.addWidget(self.stats_view)

        # Widok 2: Odtwarzacz wideo (AR)
        self.video_display = VideoDisplayWidget()
        self.display_stack.addWidget(self.video_display)

        # Inicjalizacja klasy bazowej Screen
        super().__init__(self.main_container)
        self.navigator_cb = navigator_cb

        # Ścieżki do plików wideo
        self.front_video_path = None
        self.side_video_path = None
        self.analysis_thread = None

        # Konstrukcja lewego menu zgodnie z nowymi wytycznymi
        self._build_menu()

    def _build_menu(self):
        self.options.clear()

        # Opcja 1: Perspektywa z przodu + Stan pliku
        front_txt = f"📸 Przód: {self._get_filename_or_empty(self.front_video_path)}"
        self.add_option(front_txt, self._select_front_video)
        if self.front_video_path:
            self.add_option(
                "   ❌ Wyczyść przód", lambda: self._clear_perspective("front")
            )

        # Opcja 2: Perspektywa z boku + Stan pliku
        side_txt = f"📸 Bok: {self._get_filename_or_empty(self.side_video_path)}"
        self.add_option(side_txt, self._select_side_video)
        if self.side_video_path:
            self.add_option(
                "   ❌ Wyczyść bok", lambda: self._clear_perspective("side")
            )

        # Nowe przyciski akcji
        self.add_option("📊 Statystyki Serii", self._show_static_stats)
        self.add_option("⚙️ Analiza Serii (Odtwórz AR)", self._start_video_analysis)

        self.add_option(
            "💾 Zapisz serię",
            lambda: print("[Database] Zapis serii wstrzymany do końca analizy"),
        )
        self.add_option("⬅️ Wróć", self._on_back_clicked)

    def _get_filename_or_empty(self, path):
        import os

        return os.path.basename(path) if path else "--- WYBIERZ ---"

    def _select_front_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_container,
            "Wybierz nagranie z przodu",
            "",
            "Wideo (*.mp4 *.avi *.mov)",
        )
        if file_path:
            self.front_video_path = file_path
            self._update_menu_and_refresh()

    def _select_side_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_container,
            "Wybierz nagranie z boku",
            "",
            "Wideo (*.mp4 *.avi *.mov)",
        )
        if file_path:
            self.side_video_path = file_path
            self._update_menu_and_refresh()

    def _clear_perspective(self, mode):
        if mode == "front":
            self.front_video_path = None
        elif mode == "side":
            self.side_video_path = None
        self._update_menu_and_refresh()

    def _update_menu_and_refresh(self):
        """Metoda wymuszająca przebudowanie lewego menu w AppWindow."""
        self._build_menu()
        # Wywołanie wewnętrznej struktury odświeżania menu z klasy AppWindow
        # Przekazujemy instancję rodzica okna, aby odświeżyć zaalokowane QPushButtony
        if self.main_container.window():
            window = self.main_container.window()
            if hasattr(window, "refresh_screen_menu"):
                window.refresh_screen_menu("load_set", self)

    def _show_static_stats(self):
        """Generuje wstępny szybki raport tekstowy bez uruchamiania wideo."""
        if not self.front_video_path and not self.side_video_path:
            self.lbl_stats_content.setText(
                "<span style='color:red;'>Błąd: Musisz wybrać przynajmniej jeden plik wideo!</span>"
            )
            return

        self.display_stack.setCurrentIndex(0)  # Widok tekstowy
        tak_html = "<span style='color:#00cc66;'>TAK</span>"

        self.lbl_stats_content.setText(
            f"<b>Status plików gotowych do pełnej analizy:</b><br>"
            f"Wideo z przodu: {tak_html if self.front_video_path else 'Brak'}<br>"
            f"Wideo z boku: {tak_html if self.side_video_path else 'Brak'}<br><br>"
            f"<i>Kliknij 'Analiza Serii', aby wygenerować dynamiczne powtórzenia i błędy AR.</i>"
        )

    def _start_video_analysis(self):
        if not self.front_video_path and not self.side_video_path:
            return

        # Przełącz widok na podział klatek wideo
        self.display_stack.setCurrentIndex(1)
        self.video_display.set_modes(
            bool(self.front_video_path), bool(self.side_video_path)
        )

        # Zabezpieczenie przed ponownym kliknięciem (blokowanie menu akcji)
        self._toggle_menu_buttons(enabled=False)

        # Uruchomienie przetwarzania w tle
        self.analysis_thread = VideoAnalysisThread(
            self.front_video_path, self.side_video_path
        )
        self.analysis_thread.frame_processed.connect(self.video_display.update_frames)
        self.analysis_thread.finished_analysis.connect(self._on_analysis_finished)
        self.analysis_thread.start()

    def _on_analysis_finished(self, final_stats):
        self._toggle_menu_buttons(enabled=True)
        self.display_stack.setCurrentIndex(0)  # Powrót do widoku podsumowania

        # Zliczanie wykrytych błędów z feedbacku
        errors_list = []
        if final_stats["hand_feedback"] != "OK":
            errors_list.append(f"Rozstaw dłoni: {final_stats['hand_feedback']}")
        if not final_stats["leg_correct"]:
            errors_list.append("Złe ugięcie nóg w kolanach")
        if not final_stats["body_correct"]:
            errors_list.append("Brak kąta prostego tułów-uda")

        err_str = (
            "<br>".join([f"• {e}" for e in errors_list])
            if errors_list
            else "Brak uwag (Seria poprawna)"
        )

        self.lbl_stats_content.setText(
            f"<span style='color: #00cc66; font-size: 20px;'><b>Podsumowanie ukończonej analizy:</b></span><br><br>"
            f"<b>Suma zaliczonych powtórzeń:</b> {final_stats['total_reps']}<br>"
            f"Powtórzenia (Widok Przód): {final_stats['front_reps']} | (Widok Bok): {final_stats['side_reps']}<br><br>"
            f"<span style='color: #ffcc00;'><b>Zarejestrowane nieprawidłowości:</b></span><br>{err_str}"
        )

    def _toggle_menu_buttons(self, enabled: bool):
        """Blokuje lewe menu na czas renderowania."""
        window = self.main_container.window()
        if window and hasattr(window, "menu_stack"):
            active_menu_card = window.menu_stack.currentWidget()
            if active_menu_card:
                for btn in active_menu_card.findChildren(QPushButton):
                    if "Wróć" not in btn.text():
                        btn.setEnabled(enabled)

    def _reset_all_states(self):
        """Czyści ścieżki i resetuje widok."""
        if self.analysis_thread and self.analysis_thread.isRunning():
            self.analysis_thread.stop()
        self.front_video_path = None
        self.side_video_path = None
        self.display_stack.setCurrentIndex(0)
        self.lbl_stats_content.setText(
            "Wybierz pliki wideo z menu po lewej stronie, aby rozpocząć."
        )
        self._update_menu_and_refresh()

    def _on_back_clicked(self):
        self._reset_all_states()
        self.navigator_cb("main_page")


class AnalyzeProgressScreen(Screen):
    def __init__(self, navigator_cb, load_data_cb):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)

        lbl_info = QLabel("Centrum Statystyk i Historii Treningu")
        lbl_info.setStyleSheet(
            "color: #00cc66; font-size: 20px; font-weight: bold; margin-bottom: 5px;"
        )
        lbl_info.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_info)

        self.history_widget = TrainingDataHistoryWidget()
        layout.addWidget(self.history_widget)

        super().__init__(container)
        self.add_option("Wczytaj dane treningowe", load_data_cb)
        self.add_option(
            "Jakość serii", lambda: print("[UI] Kliknięto: Analiza: Jakość serii")
        )
        self.add_option(
            "Ilość powtórzeń", lambda: print("[UI] Kliknięto: Analiza: Ilość powtórzeń")
        )
        self.add_option(
            "Czas trwania serii", lambda: print("[UI] Kliknięto: Analiza: Czas trwania")
        )
        self.add_option(
            "Liczba serii w ciągu dnia",
            lambda: print("[UI] Kliknięto: Analiza: Liczba serii/dzień"),
        )
        self.add_option("Wróć", lambda: navigator_cb("main_page"))


class ManualDefinitionScreen(Screen, QObject):
    # Sygnał wysyłany do głównej klasy w celu zapisania skonstruowanej serii
    save_requested = Signal(object)

    def __init__(self, navigator_cb, parent_widget):
        # QObject.__init__(self) musi być jawne przy wielodziedziczeniu w PySide
        QObject.__init__(self)
        self.parent_widget = parent_widget
        self.navigator_cb = navigator_cb

        self.manual_set = WorkoutSet(location="", duration=0)
        self.manual_set.execution_date = ""

        self.manual_preview = ManualPreviewWidget()
        super().__init__(self.manual_preview)

        self.add_option("📍 Lokalizacja", self._set_manual_location)
        self.add_option("⏱ Czas trwania serii", self._set_manual_duration)
        self.add_option("📅 Data i godzina", self._set_manual_datetime)
        self.add_option("＋ Dodaj powtórzenie", self._add_manual_repetition)
        self.add_option("💾 Zapisz do bazy", self._save_manual_to_db)
        self.add_option("⬅ Wróć", lambda: self.navigator_cb("create_set"))

        self._refresh_right_preview()

    def reset_set(self):
        self.manual_set = WorkoutSet(location="", duration=0)
        self.manual_set.execution_date = ""
        self._refresh_right_preview()

    def _refresh_right_preview(self):
        loc = self.manual_set.location if self.manual_set.location else "___"
        if self.manual_set.duration_seconds > 0:
            m = self.manual_set.duration_seconds // 60
            s = self.manual_set.duration_seconds % 60
            dur = f"{m}m {s}s" if m > 0 else f"{s} s"
        else:
            dur = "___"
        date = (
            self.manual_set.execution_date if self.manual_set.execution_date else "___"
        )
        self.manual_preview.update_view(loc, dur, date, self.manual_set.repetitions)

    def _set_manual_location(self):
        text, ok = QInputDialog.getText(
            self.parent_widget,
            "Lokalizacja",
            "Wpisz miejsce:",
            QLineEdit.Normal,
            self.manual_set.location,
        )
        if ok:
            self.manual_set.location = text.strip()
            self._refresh_right_preview()

    def _set_manual_duration(self):
        dialog = DurationDialog(
            current_total_seconds=self.manual_set.duration_seconds,
            parent=self.parent_widget,
        )
        if dialog.exec() == DurationDialog.Accepted:
            self.manual_set.duration_seconds = dialog.get_total_seconds()
            self._refresh_right_preview()

    def _set_manual_datetime(self):
        dialog = DateTimeDialog(parent=self.parent_widget)
        if dialog.exec() == DateTimeDialog.Accepted:
            self.manual_set.execution_date = dialog.get_date_string()
            self._refresh_right_preview()

    def _add_manual_repetition(self):
        dialog = RepetitionDialog(self.parent_widget)
        if dialog.exec() == RepetitionDialog.Accepted:
            self.manual_set.add_repetition(dialog.get_data())
            self._refresh_right_preview()

    def _save_manual_to_db(self):
        if not self.manual_set.repetitions:
            QMessageBox.warning(
                self.parent_widget, "Błąd", "Nie możesz zapisać serii bez powtórzeń!"
            )
            return

        if not self.manual_set.location:
            self.manual_set.location = "Dom"
        if not self.manual_set.execution_date:
            self.manual_set.execution_date = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        # Emitujemy obiekt serii do głównej klasy, która zajmie się plikami i bazą danych
        self.save_requested.emit(self.manual_set)
