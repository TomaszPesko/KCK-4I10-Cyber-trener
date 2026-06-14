from PySide6.QtCharts import (
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QDateTimeAxis,
    QLineSeries,
    QValueAxis,
)
from PySide6.QtCore import QDateTime, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QVBoxLayout, QWidget


class ProgressChartWidget(QWidget):
    """Natywny, ciemny widget wykresów oparty o QtCharts."""

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Inicjalizacja bazowych komponentów QtCharts
        self.chart = QChart()
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)

        # Stylizacja ciemnego motywu wykresu
        self.chart.setBackgroundVisible(
            False
        )  # Przezroczyste tło, dopasowane do contentArea
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(Qt.AlignBottom)
        self.chart.legend().setLabelColor(QColor("#dddddd"))

        self.layout.addWidget(self.chart_view)

    def clear_chart(self):
        self.chart.removeAllSeries()
        # Usuwamy stare osie, jeśli istnieją
        for axis in self.chart.axes():
            self.chart.removeAxis(axis)

    def _setup_time_axes(
        self,
        min_dt: QDateTime,
        max_dt: QDateTime,
        y_min: float,
        y_max: float,
        y_label: str,
    ):
        """Pomocnicza metoda konfigurująca osie X (Czas) oraz Y (Wartość)."""
        # Konfiguracja osi X (Czasowej)
        axis_x = QDateTimeAxis()
        axis_x.setFormat("yyyy-MM-dd")
        axis_x.setRange(min_dt, max_dt)
        axis_x.setLabelsColor(QColor("#bbbbbb"))
        axis_x.setGridLineColor(QColor("#444444"))

        # POPRAWKA: Ustawienie tytułu i koloru za pomocą setTitleBrush
        axis_x.setTitleText("Data")
        axis_x.setTitleVisible(True)
        axis_x.setTitleBrush(QBrush(QColor("#00cc66")))

        # Konfiguracja osi Y (Wartościowej)
        axis_y = QValueAxis()
        axis_y.setRange(y_min, y_max if y_max > y_min else y_min + 1)
        axis_y.setLabelsColor(QColor("#bbbbbb"))
        axis_y.setGridLineColor(QColor("#444444"))

        # POPRAWKA: Ustawienie tytułu i koloru za pomocą setTitleBrush
        axis_y.setTitleText(y_label)
        axis_y.setTitleVisible(True)
        axis_y.setTitleBrush(QBrush(QColor("#00cc66")))

        # Zapewnienie dyskretnych wartości (np. dla powtórzeń) jeśli liczby są małe
        if y_max < 10:
            axis_y.setLabelFormat("%d")

        self.chart.addAxis(axis_x, Qt.AlignBottom)
        self.chart.addAxis(axis_y, Qt.AlignLeft)
        return axis_x, axis_y

    def display_line_chart(
        self, data: list, title: str, y_label: str, is_percentage: bool = False
    ):
        """Generuje wykres liniowy.

        data: Lista krotek (execution_date_str, wartość)
        """
        self.clear_chart()
        self.chart.setTitle(title)
        self.chart.setTitleBrush(QColor("#00cc66"))

        if not data:
            return

        series = QLineSeries()
        series.setName(y_label)

        # Stylizacja linii na jaskrawy zielony kolor z motywu aplikacji
        pen = QPen(QColor("#00cc66"))
        pen.setWidth(3)
        series.setPen(pen)
        series.setPointsVisible(True)

        timestamps = []
        values = []

        for date_str, val in data:
            try:
                # Parsowanie pełnego timestampu z bazy danych
                dt = QDateTime.fromString(date_str, "yyyy-MM-dd HH:m:s")
                if not dt.isValid():
                    # Próba sparsowania samej daty jeśli brak części godzinowej
                    dt = QDateTime.fromString(date_str, "yyyy-MM-dd")

                if dt.isValid():
                    msecs = dt.toMSecsSinceEpoch()
                    series.append(msecs, val)
                    timestamps.append(dt)
                    values.append(val)
            except Exception as e:
                print(f"[Chart] Błąd parsowania daty {date_str}: {e}")

        if not timestamps:
            return

        self.chart.addSeries(series)

        # Konfiguracja osi
        min_dt = min(timestamps).addDays(-1)
        max_dt = max(timestamps).addDays(1)
        y_min = 0 if is_percentage else min(values) * 0.9
        y_max = 100 if is_percentage else max(values) * 1.1

        axis_x, axis_y = self._setup_time_axes(min_dt, max_dt, y_min, y_max, y_label)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)

    def display_bar_chart(self, data: list, title: str, y_label: str):
        """Generuje wykres słupkowy dla rozkładu serii w ciągu dnia.

        data: Lista krotek (only_date_str, count)
        """
        self.clear_chart()
        self.chart.setTitle(title)
        self.chart.setTitleBrush(QColor("#00cc66"))

        if not data:
            return

        bar_set = QBarSet("Liczba serii")
        bar_set.setColor(QColor("#00cc66"))
        bar_set.setBorderColor(QColor("#008844"))

        series = QBarSeries()
        timestamps = []
        values = []

        # Uwaga: QBarSeries domyślnie używa kategorii tekstowych, ale aby zachować osie czasu,
        # możemy zasymulować rozkład na osi DateTime mapując wartości ręcznie.
        # Jednak najbardziej natywnym i ładnym sposobem w QtCharts dla dat jest ponowne użycie QLineSeries/QScatterSeries
        # lub uproszczony wykres słupkowy. Zaimplementujmy to za pomocą precyzyjnych linii udających słupki (pionowe linie),
        # co zapobiega rozjeżdżaniu się skali czasu w QtCharts!

        for date_str, count in data:
            dt = QDateTime.fromString(date_str, "yyyy-MM-dd")
            if dt.isValid():
                # Tworzymy osobną serię dla każdego słupka pionowego, by uzyskać ładny wygląd
                line_series = QLineSeries()
                line_series.setPointsVisible(False)
                pen = QPen(QColor("#00cc66"))
                pen.setWidth(15)  # Szerokość słupka
                line_series.setPen(pen)

                msecs = dt.toMSecsSinceEpoch()
                line_series.append(msecs, 0)
                line_series.append(msecs, count)

                self.chart.addSeries(line_series)
                timestamps.append(dt)
                values.append(count)

        if not timestamps:
            return

        # Ukrywamy legendę dla wielu serii słupkowych, aby nie śmiecić widoku
        self.chart.legend().setVisible(False)

        min_dt = min(timestamps).addDays(-1)
        max_dt = max(timestamps).addDays(1)

        axis_x, axis_y = self._setup_time_axes(
            min_dt, max_dt, 0, max(values) + 1, y_label
        )

        for s in self.chart.series():
            s.attachAxis(axis_x)
            s.attachAxis(axis_y)
