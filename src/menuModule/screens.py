import json  # Import wbudowanego modułu JSON
from datetime import datetime

from PySide6.QtCore import QDateTime, QObject, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Importy klas danych z Twojego projektu
from src.include.set_data import Repetition, WorkoutSet
from src.menuModule.date_dialog import DateTimeDialog
from src.menuModule.manual_set_widget import (
    DurationDialog,
    ManualPreviewWidget,
    RepetitionDialog,
    TrainingDataHistoryWidget,
)
from src.menuModule.menu import Screen
from src.menuModule.progress_chart_widget import ProgressChartWidget
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


# ==> Replace the LoadSetScreen class in your ./menuModule/screens.py <==


class LoadSetScreen(Screen):
    def __init__(self, navigator_cb):
        self.main_container = QWidget()
        main_layout = QVBoxLayout(self.main_container)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Domain module instance setup
        self.workout_set = WorkoutSet(location="None", duration=0)

        # Display manager stacked layout
        self.display_stack = QStackedWidget()
        main_layout.addWidget(self.display_stack)

        # View State 1: Active native Tree structure preview canvas
        self.history_preview_widget = TrainingDataHistoryWidget()
        self.display_stack.addWidget(self.history_preview_widget)

        # View State 2: Active computer vision video frame pipeline
        self.video_display = VideoDisplayWidget()
        self.display_stack.addWidget(self.video_display)

        super().__init__(self.main_container)
        self.navigator_cb = navigator_cb

        self.front_video_path = None
        self.side_video_path = None
        self.analysis_thread = None

        self._build_menu()
        self._refresh_history_tree()

    def _build_menu(self):
        self.options.clear()

        # Target video file selectors
        front_txt = f"📸 Front: {self._get_filename_or_empty(self.front_video_path)}"
        self.add_option(front_txt, self._select_front_video)

        side_txt = f"📸 Side: {self._get_filename_or_empty(self.side_video_path)}"
        self.add_option(side_txt, self._select_side_video)

        # Target serialization metadata bindings
        self.add_option(f"📍 Location: {self.workout_set.location}", self._set_location)
        self.add_option(
            f"📅 Timestamp: {self.workout_set.execution_date[:16]}", self._set_datetime
        )

        # Interactive controls
        self.add_option("📊 Show Statistics (Tree)", self._show_static_stats)
        self.add_option("⚙️ Run AR Analysis View", self._start_video_analysis)
        self.add_option("💾 Save Set to Database", self._save_set_to_database)
        self.add_option("⬅️ Back", self._on_back_clicked)

    def _get_filename_or_empty(self, path):
        import os

        return os.path.basename(path) if path else "--- SELECT ---"

    def _select_front_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_container,
            "Select Front Perspective Recording",
            "",
            "Video Files (*.mp4 *.avi *.mov)",
        )
        if file_path:
            self.front_video_path = file_path
            self._trigger_background_pre_extraction()

    def _select_side_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_container,
            "Select Side Perspective Recording",
            "",
            "Video Files (*.mp4 *.avi *.mov)",
        )
        if file_path:
            self.side_video_path = file_path
            self._trigger_background_pre_extraction()

    def _trigger_background_pre_extraction(self):
        """Processes source data pipelines to instantly populate metrics without blocking UI loops."""
        if not self.front_video_path and not self.side_video_path:
            return

        from src.menuModule.video_player import run_fast_background_analysis

        extracted_reps = run_fast_background_analysis(
            self.front_video_path, self.side_video_path
        )

        self.workout_set.repetitions.clear()
        for rep_tuple in extracted_reps:
            # rep_tuple: (speed, quality, shallow, far, tempo)
            rep_obj = Repetition(
                speed=rep_tuple[0],
                quality=rep_tuple[1],
                shallow=bool(rep_tuple[2]),
                far=bool(rep_tuple[3]),
                tempo=bool(rep_tuple[4]),
            )
            self.workout_set.add_repetition(rep_obj)

        self.workout_set.duration_seconds = (
            len(extracted_reps) * 2
        )  # Approximate run delta metric
        self._refresh_history_tree()
        self._update_menu_and_refresh()

    def _set_location(self):
        text, ok = QInputDialog.getText(
            self.main_container,
            "Modify Workout Session",
            "Enter location label:",
            QLineEdit.Normal,
            self.workout_set.location,
        )
        if ok:
            self.workout_set.location = text.strip() if text.strip() else "None"
            self._refresh_history_tree()
            self._update_menu_and_refresh()

    def _set_datetime(self):
        dialog = DateTimeDialog(parent=self.main_container)
        if dialog.exec() == QDialog.Accepted:
            self.workout_set.execution_date = dialog.get_date_string()
            self._refresh_history_tree()
            self._update_menu_and_refresh()

    def _refresh_history_tree(self):
        """Transforms active runtime properties into native cached dictionary variants for tree insertion."""
        total, correct, faulty = self.workout_set.summarize_set()

        mapped_reps = []
        for r in self.workout_set.repetitions:
            mapped_reps.append(
                (
                    None,
                    None,  # Omit database database row keys
                    r.execution_speed_seconds,
                    r.quality_status,
                    1 if r.error_too_shallow else 0,
                    1 if r.error_too_far_from_chair else 0,
                    1 if r.error_lacks_tempo_control else 0,
                )
            )

        cache_contract = {
            "metadata": {
                "date": self.workout_set.execution_date,
                "location": self.workout_set.location,
                "duration": self.workout_set.duration_seconds,
                "total": total,
                "correct": correct,
                "faulty": faulty,
            },
            "repetitions": mapped_reps,
        }

        self.history_preview_widget.populate_data([cache_contract])

    def _update_menu_and_refresh(self):
        self._build_menu()
        window = self.main_container.window()
        if window and hasattr(window, "refresh_screen_menu"):
            window.refresh_screen_menu("load_set", self)

    def _show_static_stats(self):
        self.display_stack.setCurrentIndex(0)

    def _start_video_analysis(self):
        if not self.front_video_path and not self.side_video_path:
            QMessageBox.warning(
                self.main_container,
                "Missing Data Source",
                "Please bind at least one pipeline tracking target!",
            )
            return

        self.display_stack.setCurrentIndex(1)
        self.video_display.set_modes(
            bool(self.front_video_path), bool(self.side_video_path)
        )
        self._toggle_menu_buttons(enabled=False)

        self.analysis_thread = VideoAnalysisThread(
            self.front_video_path, self.side_video_path
        )
        self.analysis_thread.frame_processed.connect(self.video_display.update_frames)
        self.analysis_thread.finished_analysis.connect(self._on_analysis_finished)
        self.analysis_thread.start()

    def _on_analysis_finished(self, final_stats):
        self._toggle_menu_buttons(enabled=True)
        self.display_stack.setCurrentIndex(0)
        self._trigger_background_pre_extraction()

    def _save_set_to_database(self):
        """Forwards compiled context variables to the async database worker queue."""
        if not self.front_video_path and not self.side_video_path:
            QMessageBox.critical(
                self.main_container,
                "Serialization Halt",
                "Cannot execute storage query on unverified source tracking sets.",
            )
            return

        window = self.main_container.window()
        if window and hasattr(window, "db_module"):
            window.db_module.request_set_save(self.workout_set)
            QMessageBox.information(
                self.main_container,
                "Success",
                f"Workout transaction forwarded smoothly to database queue:\n[{self.workout_set.location}] — {len(self.workout_set.repetitions)} loops tracked.",
            )
            self._on_back_clicked()

    def _toggle_menu_buttons(self, enabled: bool):
        window = self.main_container.window()
        if window and hasattr(window, "menu_stack"):
            active_menu_card = window.menu_stack.currentWidget()
            if active_menu_card:
                for btn in active_menu_card.findChildren(QPushButton):
                    if "Back" not in btn.text():
                        btn.setEnabled(enabled)

    def _on_back_clicked(self):
        if self.analysis_thread and self.analysis_thread.isRunning():
            self.analysis_thread.stop()
        self.front_video_path = None
        self.side_video_path = None
        self.workout_set = WorkoutSet(location="None", duration=0)
        self._refresh_history_tree()
        self.display_stack.setCurrentIndex(0)
        self._update_menu_and_refresh()
        self.navigator_cb("main_page")


class AnalyzeProgressScreen(Screen):

    def __init__(self, navigator_cb, load_data_action_cb, get_db_connection_cb=None):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)

        lbl_info = QLabel("Centrum Statystyk i Historii Treningu")
        lbl_info.setStyleSheet(
            "color: #00cc66; font-size: 20px; font-weight: bold; margin-bottom: 5px;"
        )
        lbl_info.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_info)

        # !!! NOWOŚĆ: Stos widżetów do przełączania widoków (Drzewo <-> Wykres) !!!
        self.display_stack = QStackedWidget()

        # Widżet 1: Oryginalna historia (Drzewo)
        self.history_widget = TrainingDataHistoryWidget()
        self.display_stack.addWidget(self.history_widget)

        # Widżet 2: Wykresy (QtCharts)
        self.chart_widget = ProgressChartWidget()
        self.display_stack.addWidget(self.chart_widget)

        layout.addWidget(self.display_stack)

        super().__init__(container)

        self.load_data_cb = load_data_action_cb
        self.get_db_conn = get_db_connection_cb
        self.cached_sets_data = []

        # Rejestracja opcji menu bocznego
        self.add_option("Wczytaj dane treningowe", self._load_training_data)
        self.add_option("Jakość serii", self._analyze_set_quality)
        self.add_option("Ilość powtórzeń", self._analyze_reps_count)
        self.add_option("Czas trwania serii", self._analyze_duration)
        self.add_option("Liczba serii w ciągu dnia", self._analyze_sets_per_day)
        self.add_option(
            "Pokaż historię (Drzewo)", self._show_history_tree
        )  # NOWA OPCJA POWROTU DO DRZEWA
        self.add_option("Wróć", lambda: navigator_cb("main_page"))

    def _load_training_data(self):
        """Wywoływane po kliknięciu przycisku 'Wczytaj dane treningowe'."""
        file_path, _ = QFileDialog.getOpenFileName(
            self.content_widget,
            "Wybierz plik bazy danych z treningami",
            "",
            "Baza danych SQLite (*.db *.sqlite);;Wszystkie pliki (*)",
        )

        if not file_path:
            return

        # !!! TUTAJ CZYŚCIMY CAŁY CACHE I WIDOK PRZED NOWYM ZAŁADOWANIEM !!!
        self.cached_sets_data = []
        self._show_history_tree()
        self.history_widget.clear()

        # Opcjonalny komunikat o ładowaniu danych
        loading_item = QTreeWidgetItem(self.history_widget)
        loading_item.setText(0, "⌛ Wczytywanie danych z bazy... Proszę czekać.")
        loading_item.setForeground(0, QBrush(QColor("#ffcc00")))

        if self.load_data_cb:
            self.load_data_cb(file_path)

    def handle_async_data_loaded(self, raw_sets_data):
        """Slot wywoływany automatycznie przy każdym odebranym pakiecie danych z db_module."""

        # 1. Sprawdzamy co przysłał db_module.
        # Jeśli to pojedyncza seria (słownik lub krotka), dodajemy ją do naszego bufora w RAM
        if isinstance(raw_sets_data, (dict, tuple, list)) and not isinstance(
            raw_sets_data, list
        ):
            # Wyciągamy unikalny wyróżnik (datę), aby uniknąć duplikacji w buforze
            exec_date = (
                raw_sets_data.get("metadata", {}).get("date")
                if isinstance(raw_sets_data, dict)
                else raw_sets_data[1]
            )

            # Sprawdzamy czy mamy już serię z tą datą w cache
            istnieje = False
            for s in self.cached_sets_data:
                S_date = (
                    s.get("metadata", {}).get("date") if isinstance(s, dict) else s[1]
                )
                if S_date == exec_date:
                    istnieje = True
                    break

            if not istnieje:
                self.cached_sets_data.append(raw_sets_data)

        elif isinstance(raw_sets_data, list):
            # Jeśli db_module przysłałby jednak całą listę naraz (lub to lista powtórzeń)
            # Sprawdzamy czy to lista słowników/krotek serii, czy coś innego
            if raw_sets_data and isinstance(raw_sets_data[0], (dict, tuple)):
                self.cached_sets_data = raw_sets_data
            else:
                # Jeśli to dziwny format, na wszelki wypadek zabezpieczamy dane
                if raw_sets_data not in self.cached_sets_data:
                    self.cached_sets_data.append(raw_sets_data)

        # 2. Przekazujemy do manual_set_widget ZAWSZE pełną, skumulowaną listę serii.
        # Nawet jeśli metoda .populate_data() wykona .clear(), to i tak zaraz odtworzy
        # wszystkie dotychczas zebrane serie z naszej listy!
        if self.cached_sets_data:
            self.history_widget.populate_data(self.cached_sets_data)

        self._show_history_tree()

    def _check_data_ready(self) -> bool:
        """Pomocnicza weryfikacja dostępności bazy danych."""
        if not self.cached_sets_data:
            self.display_stack.setCurrentWidget(self.chart_widget)
            self.chart_widget.clear_chart()
            self.chart_widget.chart.setTitle(
                "Brak danych! Najpierw kliknij 'Wczytaj dane treningowe' i wybierz plik bazy."
            )
            self.chart_widget.chart.setTitleBrush(QBrush(QColor("#cc0000")))
            return False
        return True

    def _show_history_tree(self):
        """Przełącza stos widżetów z powrotem na drzewiaste zestawienie danych."""
        self.display_stack.setCurrentWidget(self.history_widget)

    def _analyze_set_quality(self):
        """Wykres jakości serii (procent poprawnego wykonania)."""
        if not self._check_data_ready():
            return

        # Przełączamy stos widżetów na widok wykresu
        self.display_stack.setCurrentWidget(self.chart_widget)

        chart_data = []
        for row in self.cached_sets_data:
            meta = row["metadata"]
            if meta["total"] > 0:
                quality_percent = (meta["correct"] / meta["total"]) * 100.0
                chart_data.append((meta["date"], quality_percent))

        chart_data.sort(key=lambda x: x[0])
        self.chart_widget.display_line_chart(
            data=chart_data,
            title="Analiza Postępów: Jakość Wykonania Serii",
            y_label="Procent poprawnych powtórzeń (%)",
            is_percentage=True,
        )

    def _analyze_reps_count(self):
        """Wykres całkowitej ilości powtórzeń."""
        if not self._check_data_ready():
            return

        self.display_stack.setCurrentWidget(self.chart_widget)

        chart_data = [
            (row["metadata"]["date"], row["metadata"]["total"])
            for row in self.cached_sets_data
        ]
        chart_data.sort(key=lambda x: x[0])

        self.chart_widget.display_line_chart(
            data=chart_data,
            title="Analiza Postępów: Liczba Powtórzeń w Seriach",
            y_label="Suma powtórzeń (reps)",
        )

    def _analyze_duration(self):
        """Wykres czasu trwania serii."""
        if not self._check_data_ready():
            return

        self.display_stack.setCurrentWidget(self.chart_widget)

        chart_data = [
            (row["metadata"]["date"], row["metadata"]["duration"])
            for row in self.cached_sets_data
        ]
        chart_data.sort(key=lambda x: x[0])

        self.chart_widget.display_line_chart(
            data=chart_data,
            title="Analiza Postępów: Czas Trwania Serii",
            y_label="Czas (sekundy)",
        )

    def _analyze_sets_per_day(self):
        """Wykres liczby serii w ciągu dnia (agregowany z cache)."""
        if not self._check_data_ready():
            return

        self.display_stack.setCurrentWidget(self.chart_widget)

        daily_counts = {}
        for row in self.cached_sets_data:
            exec_date = row["metadata"]["date"]
            if exec_date and len(exec_date) >= 10:
                date_only = exec_date[:10]
                daily_counts[date_only] = daily_counts.get(date_only, 0) + 1

        sorted_daily_data = sorted(daily_counts.items())
        self.chart_widget.display_bar_chart(
            data=sorted_daily_data,
            title="Analiza Częstotliwości: Liczba Serii Wykonanych w Ciągu Dnia",
            y_label="Liczba serii",
        )


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

        # Rejestracja opcji menu bocznego (ZMIANA NA JSON)
        self.add_option("📍 Lokalizacja", self._set_manual_location)
        self.add_option("⏱ Czas trwania serii", self._set_manual_duration)
        self.add_option("📅 Data i godzina", self._set_manual_datetime)
        self.add_option("＋ Dodaj powtórzenie", self._add_manual_repetition)
        self.add_option(
            "📥 Importuj z JSON", self._import_from_json
        )  # POPRAWIONE NA JSON
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
        if dialog.exec() == DurationDialog.Accepted:
            self.manual_set.execution_date = dialog.get_date_string()
            self._refresh_right_preview()

    def _add_manual_repetition(self):
        dialog = RepetitionDialog(self.parent_widget)
        if dialog.exec() == RepetitionDialog.Accepted:
            self.manual_set.add_repetition(dialog.get_data())
            self._refresh_right_preview()

    def _import_from_json(self):
        """Wczytuje serie z JSON i zapisuje bezpośrednio do Twojej bazy danych SQLite (tabele 'sets' i 'repetitions'),
        całkowicie eliminując pętle okien modalnych.
        """
        import sqlite3  # Import lokalny dla bezpieczeństwa

        # 1. Wybór pliku źródłowego JSON
        json_path, _ = QFileDialog.getOpenFileName(
            self.content_widget,
            "Wybierz plik JSON ze strukturą serii",
            "",
            "Pliki JSON (*.json)",
        )
        if not json_path:
            return

        # 2. Jednorazowe pytanie o bazę docelową
        db_path, _ = QFileDialog.getSaveFileName(
            self.content_widget,
            "Wybierz plik docelowej bazy danych (.db) lub utwórz nowy",
            "",
            "Baza danych SQLite (*.db *.sqlite);;Wszystkie pliki (*)",
        )
        if not db_path:
            return

        conn = None
        try:
            # Wczytanie i parsowanie pliku JSON
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                series_list = [data]
            elif isinstance(data, list):
                series_list = data
            else:
                raise ValueError(
                    "Niepoprawna struktura JSON. Oczekiwano słownika lub listy."
                )

            # 3. BEZPOŚREDNIE POŁĄCZENIE Z BAZĄ SQLITE - TWOJA STRUKTURA
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Aktywujemy klucze obce
            cursor.execute("PRAGMA foreign_keys = ON;")

            # Upewniamy się, że tabele istnieją (dokładna kopia Twojej definicji)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_date TEXT, location TEXT, duration_seconds INTEGER,
                    total_reps INTEGER, correct_reps INTEGER, faulty_reps INTEGER
                )""")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS repetitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, set_id INTEGER,
                    execution_speed_seconds REAL, quality_status TEXT,
                    error_too_shallow INTEGER, error_too_far_from_chair INTEGER, error_lacks_tempo_control INTEGER,
                    FOREIGN KEY(set_id) REFERENCES sets(id) ON DELETE CASCADE
                )""")

            saved_counter = 0

            # Przetwarzamy każdą serię z pliku JSON
            for item_data in series_list:
                metadata = item_data.get("metadata", {})
                xml_date = metadata.get("date", "")
                xml_loc = metadata.get("location", "Import JSON")
                xml_dur = int(metadata.get("duration_seconds", 0))

                if not xml_date:
                    xml_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                repetitions_list = item_data.get("repetitions", [])
                if not repetitions_list:
                    continue  # Pomiń puste serie

                # Wyliczamy statystyki serii wymagane przez Twoją tabelę 'sets'
                total_reps = len(repetitions_list)
                correct_reps = sum(
                    1 for r in repetitions_list if r.get("quality") == "Correct"
                )
                faulty_reps = total_reps - correct_reps

                # Wstawienie rekordu do tabeli 'sets'
                cursor.execute(
                    """
                    INSERT INTO sets (execution_date, location, duration_seconds, total_reps, correct_reps, faulty_reps)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (xml_date, xml_loc, xml_dur, total_reps, correct_reps, faulty_reps),
                )

                set_id = (
                    cursor.lastrowid
                )  # Pobieramy ID wygenerowane przez Twoją tabelę 'sets'

                # Wstawienie wszystkich powtórzeń do tabeli 'repetitions'
                for rep_data in repetitions_list:
                    speed = float(rep_data.get("speed", 2.0))
                    quality_status = rep_data.get("quality", "Correct")

                    errors = rep_data.get("errors", {})
                    # Mapowanie nowych błędów na kolumny w Twojej bazie danych:
                    # legs_bent -> za płytko, rozstaw rąk -> za daleko od krzesła, brak tempa -> lacks tempo
                    error_too_shallow = 1 if bool(errors.get("legs_bent", False)) else 0
                    error_too_far_from_chair = (
                        1
                        if (
                            bool(errors.get("too_narrow", False))
                            or bool(errors.get("too_wide", False))
                        )
                        else 0
                    )
                    error_lacks_tempo_control = (
                        1 if bool(errors.get("bad_torso_angle", False)) else 0
                    )

                    cursor.execute(
                        """
                        INSERT INTO repetitions (
                            set_id, execution_speed_seconds, quality_status, 
                            error_too_shallow, error_too_far_from_chair, error_lacks_tempo_control
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            set_id,
                            speed,
                            quality_status,
                            error_too_shallow,
                            error_too_far_from_chair,
                            error_lacks_tempo_control,
                        ),
                    )

                saved_counter += 1

            # Zatwierdzamy całą transakcję
            conn.commit()

            # Reset podglądu interfejsu
            self.reset_set()

            # Powiadomienie głównego db_module o nowej bazie w celu odświeżenia struktur
            if hasattr(self.parent_widget, "db_module"):
                self.parent_widget.db_module.db_path = db_path
                if hasattr(self.parent_widget.db_module, "request_all_data"):
                    self.parent_widget.db_module.request_all_data()

            QMessageBox.information(
                self.parent_widget,
                "Sukces importu",
                f"Pomyślnie przetworzono plik JSON!\n"
                f"Zapisano {saved_counter} serii bezpośrednio do bazy danych:\n{db_path}",
            )

        except Exception as e:
            if conn:
                conn.rollback()
            QMessageBox.critical(
                self.parent_widget,
                "Błąd zapisu bazy",
                f"Wystąpił problem podczas bezpośredniego zapisu do struktur Twojej bazy danych:\n{str(e)}",
            )
        finally:
            if conn:
                conn.close()

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

        # Emitujemy obiekt serii do głównej klasy
        self.save_requested.emit(self.manual_set)
