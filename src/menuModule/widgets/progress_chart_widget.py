from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QDateTimeAxis,
    QLineSeries,
    QScatterSeries,
    QSplineSeries,
    QValueAxis,
)
from PySide6.QtCore import QDateTime, QMargins, QPoint, Qt
from PySide6.QtGui import QBrush, QColor, QCursor, QFont, QPainter, QPen
from PySide6.QtWidgets import QToolTip, QVBoxLayout, QWidget


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
        """Generuje gładką linię trendu przy użyciu nieliniowej regresji wielomianowej stopnia 3."""
        self.clear_chart()
        self.chart.setTitle(title)
        self.chart.setTitleBrush(QColor("#00cc66"))

        if not data:
            return

        # Seria 1: Gładka linia trendu (Regresja Wielomianowa)
        trend_series = QLineSeries()
        trend_series.setName(f"{y_label} (Ogólny Trend)")

        pen = QPen(QColor("#00cc66"))
        pen.setWidth(4)  # Grubsza linia dla czytelności trendu
        trend_series.setPen(pen)

        # Seria 2: Rzeczywiste punkty treningowe (Scatter)
        scatter_series = QScatterSeries()
        scatter_series.setName("Konkretne treningi")
        scatter_series.setMarkerShape(QScatterSeries.MarkerShapeCircle)
        scatter_series.setMarkerSize(8)
        scatter_series.setBrush(QBrush(QColor("#ffcc00")))
        scatter_series.setPen(QPen(QColor("#ffaa00"), 1))

        timestamps = []
        x_indices = (
            []
        )  # Czas zmapowany na sekundy/dni od początku dla stabilności numerycznej
        y_values = []

        # --- 1. Parsowanie danych ---
        for date_str, val in data:
            try:
                dt = QDateTime.fromString(date_str, Qt.ISODate)
                if not dt.isValid():
                    dt = QDateTime.fromString(date_str, "yyyy-MM-dd HH:mm:ss")
                if not dt.isValid():
                    dt = QDateTime.fromString(date_str, "yyyy-MM-dd")

                if dt.isValid():
                    msecs = dt.toMSecsSinceEpoch()
                    scatter_series.append(msecs, val)  # Dodajemy surowy punkt pomiarowy
                    timestamps.append(dt)
                    y_values.append(val)
            except Exception as e:
                print(f"[Chart Error] {e}")

        if not timestamps:
            return

        # --- 2. Algorytm Regresji Wielomianowej stopnia 3 (Najmniejsze kwadraty) ---
        # Mapujemy milisekundy na mniejsze wartości (np. sekundy od pierwszego treningu)
        # zapobiega to potężnym przepełnieniom zmiennych przy potęgowaniu timestampów (C++ Overflow)
        t0 = min(timestamps).toMSecsSinceEpoch()
        x_values = [(t.toMSecsSinceEpoch() - t0) / 1000.0 for t in timestamps]
        n = len(x_values)

        # Jeśli mamy za mało danych na wielomian stopnia 3, domyślnie rysujemy prostą linię łączącą
        if n < 4:
            for t, y in zip(timestamps, y_values):
                trend_series.append(t.toMSecsSinceEpoch(), y)
        else:
            # Tworzymy macierz i wektor do rozwiązania układu równań liniowych wielomianu stopnia 3
            # Równanie: y = a*x^3 + b*x^2 + c*x + d
            sums_x = [0.0] * 7  # Od sum(x^0) do sum(x^6)
            for x in x_values:
                for power in range(7):
                    sums_x[power] += x**power

            sum_y = sum(y_values)
            sum_xy = sum(x * y for x, y in zip(x_values, y_values))
            sum_x2y = sum((x**2) * y for x, y in zip(x_values, y_values))
            sum_x3y = sum((x**3) * y for x, y in zip(x_values, y_values))

            # Prosta eliminacja Gaussa do wyznaczenia współczynników a, b, c, d
            # Budujemy macierz rozszerzoną układu
            matrix = [
                [sums_x[6], sums_x[5], sums_x[4], sums_x[3], sum_x3y],
                [sums_x[5], sums_x[4], sums_x[3], sums_x[2], sum_x2y],
                [sums_x[4], sums_x[3], sums_x[2], sums_x[1], sum_xy],
                [sums_x[3], sums_x[2], sums_x[1], sums_x[0], sum_y],
            ]

            # Eliminacja w dół
            for i in range(4):
                for j in range(i + 1, 4):
                    factor = matrix[j][i] / matrix[i][i]
                    for k in range(i, 5):
                        matrix[j][k] -= factor * matrix[i][k]

            # Podstawienie wsteczne
            coefs = [0.0] * 4
            for i in range(3, -1, -1):
                coefs[i] = matrix[i][4]
                for j in range(i + 1, 4):
                    coefs[i] -= matrix[i][j] * coefs[j]
                coefs[i] /= matrix[i][i]

            a, b, c, d = coefs  # Nasze dopasowane współczynniki trendu

            # --- 3. Generowanie gładkiej krzywej trendu ---
            # Próbkujemy wyliczone równanie w 50 równomiernych punktach od początku do końca osi czasu
            start_x = min(x_values)
            end_x = max(x_values)
            step = (end_x - start_x) / 50.0

            for i in range(51):
                curr_x = start_x + (i * step)
                # Wyliczamy wartość Y z wielomianu regresji
                pred_y = a * (curr_x**3) + b * (curr_x**2) + c * curr_x + d

                # Zabezpieczenie dla procentów, aby trend nie wystrzelił poza logiczną skalę 0-100%
                if is_percentage:
                    pred_y = max(0.0, min(100.0, pred_y))

                # Mapujemy z powrotem na milisekundowy timestamp osi X
                curr_msecs = t0 + (curr_x * 1000.0)
                trend_series.append(curr_msecs, pred_y)

        # Dodanie serii i konfiguracja osi
        self.chart.addSeries(trend_series)
        self.chart.addSeries(scatter_series)

        min_dt = min(timestamps).addDays(-2)
        max_dt = max(timestamps).addDays(2)
        y_min = 0 if is_percentage else min(y_values) * 0.9
        y_max = 100 if is_percentage else max(y_values) * 1.1

        axis_x, axis_y = self._setup_time_axes(min_dt, max_dt, y_min, y_max, y_label)

        trend_series.attachAxis(axis_x)
        trend_series.attachAxis(axis_y)
        scatter_series.attachAxis(axis_x)
        scatter_series.attachAxis(axis_y)

    def display_bar_chart(self, data: list, title: str, y_label: str):
        """Generuje interaktywny wykres słupkowy na osi czasu z równomiernie rozłożonymi datami."""
        self.clear_chart()
        self.chart.setTitle(title)
        self.chart.setTitleBrush(QColor("#00cc66"))

        title_font = QFont("Arial", 14, QFont.Bold)
        self.chart.setTitleFont(title_font)

        if not data:
            return

        # Margines na dole zapewniający pełną widoczność dat osi czasu
        self.chart.setMargins(QMargins(25, 10, 20, 45))

        timestamps = []
        values = []
        self.bar_data_cache = []  # Bufor dla podpowiedzi hovered

        # Dynamicznie dobieramy szerokość słupka (grubość linii pen) w zależności od gęstości danych
        # Im więcej dni w bazie, tym słupki powinny być nieco węższe, by zachować bezpieczny padding
        total_days = len(data)
        bar_width = 14 if total_days < 15 else 8 if total_days < 40 else 4

        # Renderujemy KAŻDY słupek na swoim dokładnym miejscu w czasie
        for idx, (date_str, count) in enumerate(data):
            dt = QDateTime.fromString(date_str, Qt.ISODate)
            if not dt.isValid():
                dt = QDateTime.fromString(date_str, "yyyy-MM-dd")

            if dt.isValid():
                # Tworzymy pionową serię słupkową
                bar_line = QLineSeries()
                bar_line.setPointsVisible(False)

                # Jaskrawy zielony kolor z ciemniejszym, eleganckim akcentem
                pen = QPen(QColor("#00cc66"))
                pen.setWidth(bar_width)
                bar_line.setPen(pen)

                msecs = dt.toMSecsSinceEpoch()
                bar_line.append(msecs, 0)
                bar_line.append(msecs, count)

                self.chart.addSeries(bar_line)

                # Zapisujemy do bufora identyfikatory indeksów dla zdarzeń myszy
                self.bar_data_cache.append((msecs, date_str, count, bar_width))
                timestamps.append(dt)
                values.append(count)

        if not timestamps:
            return

        self.chart.legend().setVisible(False)

        axis_x = QDateTimeAxis()
        axis_x.setFormat("yyyy-MM-dd")
        axis_x.setLabelsColor(QColor("#dddddd"))
        axis_x.setGridLineColor(QColor("#444444"))
        axis_x.setLabelsFont(QFont("Arial", 10))
        axis_x.setLabelsAngle(0)  # Czyste, poziome napisy

        axis_x.setTickCount(5)

        min_dt = min(timestamps).addDays(-2)
        max_dt = max(timestamps).addDays(2)
        axis_x.setRange(min_dt, max_dt)
        self.chart.addAxis(axis_x, Qt.AlignBottom)

        max_val = max(values) if values else 5
        axis_y = QValueAxis()
        axis_y.setRange(0, max_val + 1)
        axis_y.setLabelFormat("%d")
        axis_y.setTitleText(y_label)
        axis_y.setTitleBrush(QColor("#00cc66"))
        axis_y.setLabelsColor(QColor("#dddddd"))
        axis_y.setGridLineColor(QColor("#444444"))
        axis_y.setLabelsFont(QFont("Arial", 10))
        self.chart.addAxis(axis_y, Qt.AlignLeft)

        for s in self.chart.series():
            s.attachAxis(axis_x)
            s.attachAxis(axis_y)

        if hasattr(self, "chart_view") and self.chart_view:
            self.chart_view.setMouseTracking(True)
            self.chart_view.mouseMoveEvent = self._on_chart_mouse_move

    def _on_chart_mouse_move(self, event):
        """Inteligentny, ciągły skaner pozycji myszy mapujący współrzędne pikseli na punkty czasu osi X."""
        pos = event.position()
        mapped_point = self.chart.mapToValue(pos)
        mouse_msecs = mapped_point.x()
        mouse_y = mapped_point.y()

        hover_hit = False

        for msecs, date_str, count, width in self.bar_data_cache:
            time_tolerance = 12 * 60 * 60 * 1000

            if abs(mouse_msecs - msecs) < time_tolerance and 0 <= mouse_y <= count:
                suffix = (
                    "serie" if count in [2, 3, 4] else "serii" if count > 4 else "seria"
                )
                tooltip_text = (
                    f"<b>Data:</b> {date_str}<br><b>Wykonano:</b> {count} {suffix}"
                )

                QToolTip.showText(QCursor.pos(), tooltip_text, self.chart_view)
                hover_hit = True
                break

        if not hover_hit:
            QToolTip.hideText()

    def _on_bar_hovered(self, status: bool, index: int, bar_set: QBarSet):
        """Slot wyświetlający czysty dymek podpowiedzi w aktualnej pozycji myszy na ekranie."""
        if status:
            if 0 <= index < len(self.bar_data_cache):
                date_str, count = self.bar_data_cache[index]
                suffix = (
                    "serie" if count in [2, 3, 4] else "serii" if count > 4 else "seria"
                )

                tooltip_text = (
                    f"<b>Data:</b> {date_str}<br><b>Wykonano:</b> {count} {suffix}"
                )

                # POPRAWKA: Używamy globalnej pozycji kursora myszy za pomocą QCursor.pos()
                # self.chart_view (lub self, jeśli widget dziedziczy po QChartView) jako widget nadrzędny
                view_widget = getattr(self, "chart_view", self)
                QToolTip.showText(QCursor.pos(), tooltip_text, view_widget)
        else:
            QToolTip.hideText()
