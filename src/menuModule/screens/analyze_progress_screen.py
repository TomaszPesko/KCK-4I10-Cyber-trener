from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QStackedWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.menuModule.menu import Screen
from src.menuModule.widgets.progress_chart_widget import ProgressChartWidget
from src.menuModule.widgets.training_data_history_widget import (
    TrainingDataHistoryWidget,
)


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

        self.display_stack = QStackedWidget()

        self.history_widget = TrainingDataHistoryWidget()
        self.display_stack.addWidget(self.history_widget)

        self.chart_widget = ProgressChartWidget()
        self.display_stack.addWidget(self.chart_widget)

        layout.addWidget(self.display_stack)

        super().__init__(container)

        self.load_data_cb = load_data_action_cb
        self.get_db_conn = get_db_connection_cb
        self.cached_sets_data = []

        self.add_option("Wczytaj dane treningowe", self._load_training_data)
        self.add_option("Jakość serii", self._analyze_set_quality)
        self.add_option("Ilość powtórzeń", self._analyze_reps_count)
        self.add_option("Czas trwania serii", self._analyze_duration)
        self.add_option("Liczba serii w ciągu dnia", self._analyze_sets_per_day)
        self.add_option("Pokaż historię (Drzewo)", self._show_history_tree)
        self.add_option("Wróć", lambda: navigator_cb("main_page"))

    def _load_training_data(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.content_widget,
            "Wybierz plik bazy danych z treningami",
            "",
            "Baza danych SQLite (*.db *.sqlite);;Wszystkie pliki (*)",
        )

        if not file_path:
            return

        self.cached_sets_data.clear()
        self.history_widget.clear()
        self.chart_widget.clear_chart()
        self._show_history_tree()

        loading_item = QTreeWidgetItem(self.history_widget)
        loading_item.setText(0, "⌛ Wczytywanie danych z bazy... Proszę czekać.")
        loading_item.setForeground(0, QBrush(QColor("#ffcc00")))

        if self.load_data_cb:
            self.load_data_cb(file_path)

    def handle_async_data_loaded(self, raw_sets_data):
        if isinstance(raw_sets_data, (dict, tuple)) and not isinstance(
            raw_sets_data, list
        ):
            exec_date = (
                raw_sets_data.get("metadata", {}).get("date")
                if isinstance(raw_sets_data, dict)
                else raw_sets_data[1]
            )

            is_duplicate = False
            for record in self.cached_sets_data:
                existing_date = (
                    record.get("metadata", {}).get("date")
                    if isinstance(record, dict)
                    else record[1]
                )
                if existing_date == exec_date:
                    is_duplicate = True
                    break

            if not is_duplicate:
                self.cached_sets_data.append(raw_sets_data)

        elif isinstance(raw_sets_data, list):
            if raw_sets_data and isinstance(raw_sets_data[0], (dict, tuple)):
                self.cached_sets_data = list(raw_sets_data)
            else:
                if raw_sets_data not in self.cached_sets_data:
                    self.cached_sets_data.append(raw_sets_data)

        if self.cached_sets_data:
            self.history_widget.populate_data(self.cached_sets_data)

    def _check_data_ready(self) -> bool:
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
        self.display_stack.setCurrentWidget(self.history_widget)

    def _analyze_set_quality(self):
        """Calculates fine-grained performance indices based on composite non-error point aggregates."""
        if not self._check_data_ready():
            return

        self.display_stack.setCurrentWidget(self.chart_widget)
        chart_data = []

        for row in self.cached_sets_data:
            meta = row["metadata"]
            repetitions = row.get("repetitions", [])

            if len(repetitions) > 0:
                total_set_percentage = 0.0
                for rep in repetitions:
                    if isinstance(rep, dict):
                        errors_map = rep.get("errors", {})
                        shallow = (
                            1
                            if bool(errors_map.get("legs_bent", False))
                            or bool(errors_map.get("too_shallow", False))
                            else 0
                        )
                        far = (
                            1
                            if (
                                bool(errors_map.get("too_narrow", False))
                                or bool(errors_map.get("too_wide", False))
                                or bool(errors_map.get("too_far_from_chair", False))
                            )
                            else 0
                        )
                        tempo = (
                            1
                            if bool(errors_map.get("bad_torso_angle", False))
                            or bool(errors_map.get("lacks_tempo_control", False))
                            else 0
                        )
                    else:
                        length = len(rep)
                        if length == 5:
                            shallow = int(rep[2])
                            far = int(rep[3])
                            tempo = int(rep[4])
                        elif length >= 7:
                            shallow = int(rep[4])
                            far = int(rep[5])
                            tempo = int(rep[6])
                        else:
                            shallow = int(rep[1]) if length > 1 else 0
                            far = 0
                            tempo = 0

                    active_errors_count = shallow + far + tempo

                    # System sportowy rygorystyczny - 1 błąd = oblane powtórzenie (0%)
                    rep_percentage = 100.0 if active_errors_count == 0 else 0.0
                    total_set_percentage += rep_percentage

                calculated_set_average = total_set_percentage / len(repetitions)
                chart_data.append((meta["date"], calculated_set_average))
            else:
                if meta.get("total", 0) > 0:
                    ratio_percentage = (meta["correct"] / meta["total"]) * 100.0
                    chart_data.append((meta["date"], ratio_percentage))

        chart_data.sort(key=lambda x: x[0])

        self.chart_widget.display_line_chart(
            data=chart_data,
            title="Analiza Postępów: Procentowa Jakość Wykonania Powtórzeń",
            y_label="Średnia dokładność serii (%)",
            is_percentage=True,
        )

    def _analyze_reps_count(self):
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
        if not self._check_data_ready():
            return

        self.display_stack.setCurrentWidget(self.chart_widget)
        daily_counts = {}

        for row in self.cached_sets_data:
            exec_date = row["metadata"]["date"]
            if exec_date and len(exec_date) >= 10:
                date_only = exec_date[:10]
                daily_counts[date_only] = daily_counts.get(date_only, 0) + 1

        # Sortujemy chronologicznie
        sorted_daily_data = sorted(daily_counts.items())

        self.chart_widget.display_bar_chart(
            data=sorted_daily_data,
            title="Analiza Częstotliwości: Liczba Serii Wykonanych w Ciągu Dnia",
            y_label="Liczba serii",
        )
