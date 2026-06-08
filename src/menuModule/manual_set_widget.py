from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.include.set_data import Repetition


class DurationDialog(QDialog):
    """Popup dialog to set workout duration in minutes and seconds."""

    def __init__(self, current_total_seconds: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ustaw czas trwania")
        self.setMinimumWidth(280)

        self.setStyleSheet("""
            QDialog { background-color: rgb(40, 40, 40); border: 2px solid #00cc66; border-radius: 10px; }
            QLabel { color: #dddddd; font-size: 14px; }
            QSpinBox { background-color: rgb(60, 60, 60); color: white; border: 1px solid #555; border-radius: 5px; padding: 5px; font-size: 14px; }
            QPushButton { background-color: rgba(60, 60, 60, 220); color: white; border-radius: 8px; padding: 6px; font-size: 14px; }
            QPushButton:hover { background-color: #00cc66; color: black; }
        """)

        layout = QVBoxLayout(self)

        # Wyliczenie aktualnych minut i sekund z przekazanej liczby sekund
        init_min = current_total_seconds // 60
        init_sec = current_total_seconds % 60

        inputs_layout = QHBoxLayout()

        # Minuty
        min_vbox = QVBoxLayout()
        min_vbox.addWidget(QLabel("Minuty:"))
        self.spin_minutes = QSpinBox(self)
        self.spin_minutes.setRange(0, 60)
        self.spin_minutes.setValue(init_min)
        min_vbox.addWidget(self.spin_minutes)

        # Sekundy
        sec_vbox = QVBoxLayout()
        sec_vbox.addWidget(QLabel("Sekundy:"))
        self.spin_seconds = QSpinBox(self)
        self.spin_seconds.setRange(0, 59)
        self.spin_seconds.setValue(init_sec)
        sec_vbox.addWidget(self.spin_seconds)

        inputs_layout.addLayout(min_vbox)
        inputs_layout.addLayout(sec_vbox)
        layout.addLayout(inputs_layout)

        layout.addSpacing(10)

        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Zapisz")
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Anuluj")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def get_total_seconds(self) -> int:
        return (self.spin_minutes.value() * 60) + self.spin_seconds.value()


class RepetitionDialog(QDialog):
    """Popup dialog to manually configure a single exercise repetition."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dodaj Powtórzenie")
        self.setMinimumWidth(320)

        self.setStyleSheet("""
            QDialog { background-color: rgb(40, 40, 40); border: 2px solid #00cc66; border-radius: 10px; }
            QLabel { color: #dddddd; font-size: 14px; }
            QLineEdit { background-color: rgb(60, 60, 60); color: white; border: 1px solid #555; border-radius: 5px; padding: 5px; }
            QCheckBox { color: white; font-size: 13px; }
            QPushButton { background-color: rgba(60, 60, 60, 220); color: white; border-radius: 8px; padding: 6px; font-size: 14px; }
            QPushButton:hover { background-color: #00cc66; color: black; }
        """)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Czas wykonania (sekundy):"))
        self.speed_input = QLineEdit("2.5")
        layout.addWidget(self.speed_input)

        layout.addWidget(QLabel("Błędy powtórzenia:"))
        self.cb_shallow = QCheckBox("Za płytko (too shallow)")
        self.cb_far = QCheckBox("Za daleko od krzesła (too far)")
        self.cb_tempo = QCheckBox("Brak kontroli tempa (lacks tempo)")

        layout.addWidget(self.cb_shallow)
        layout.addWidget(self.cb_far)
        layout.addWidget(self.cb_tempo)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Dodaj")
        self.btn_add.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Anuluj")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def get_data(self) -> Repetition:
        try:
            speed = float(self.speed_input.text())
        except ValueError:
            speed = 0.0

        shallow = self.cb_shallow.isChecked()
        far = self.cb_far.isChecked()
        tempo = self.cb_tempo.isChecked()

        quality = "Faulty" if (shallow or far or tempo) else "Correct"
        return Repetition(speed, quality, shallow, far, tempo)


class ManualPreviewWidget(QWidget):
    """Right-side canvas displaying live text summary of the configured workout set."""

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.lbl_title = QLabel("Podgląd Tworzonej Serii (Ręcznie)")
        self.lbl_title.setStyleSheet(
            "color: #00cc66; font-size: 26px; font-weight: bold; margin-bottom: 15px;"
        )
        self.lbl_title.setAlignment(Qt.AlignCenter)

        self.lbl_metadata = QLabel()
        self.lbl_metadata.setStyleSheet(
            "color: #dddddd; font-size: 16px; line-height: 160%;"
        )
        self.lbl_metadata.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_metadata)
        self.update_view("___", "___", "___", [])

    def update_view(self, location: str, duration: str, date: str, repetitions: list):
        total = len(repetitions)
        correct = sum(1 for r in repetitions if r.quality_status == "Correct")
        faulty = total - correct

        text = (
            f"<b>Data i godzina:</b> {date}<br>"
            f"<b>Lokalizacja:</b> {location}<br>"
            f"<b>Czas trwania serii:</b> {duration}<br><br>"
            f"<span style='color: #00cc66; font-size: 18px;'><b>Suma powtórzeń:</b> {total}</span><br>"
            f"Poprawne: {correct}  |  Z błędami: {faulty}"
        )
        self.lbl_metadata.setText(text)


class TrainingDataHistoryWidget(QWidget):
    """Widget structured to display loaded historical sets and nested repetitions in a tree structure."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(
            ["Parametr / Powtórzenie", "Status / Wartość", "Wykryte błędy"]
        )
        self.tree.header().setSectionResizeMode(QHeaderView.Stretch)

        # Stylizacja dopasowana do ciemnego motywu CyberTrenera
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: rgb(35, 35, 35);
                color: #dddddd;
                border: 1px solid #555;
                border-radius: 6px;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: rgb(50, 50, 50);
                color: #00cc66;
                padding: 6px;
                font-weight: bold;
                border: 1px solid #333;
            }
            QTreeWidget::item {
                padding: 6px;
                border-bottom: 1px solid #2d2d2d;
            }
            QTreeWidget::item:hover {
                background-color: rgba(0, 204, 102, 30);
            }
        """)
        layout.addWidget(self.tree)

    def populate_data(self, dataset: list):
        """Clears the view and builds nested nodes from the dataset array."""
        self.tree.clear()

        if not dataset:
            root_item = QTreeWidgetItem(
                self.tree,
                ["Brak danych", "Wybierz plik bazy danych lub zrób trening", ""],
            )
            return

        for index, set_data in enumerate(dataset, 1):
            meta = set_data["metadata"]

            # Konwersja czasu trwania na minuty i sekundy
            m, s = meta["duration"] // 60, meta["duration"] % 60
            dur_str = f"{m}m {s}s" if m > 0 else f"{s}s"

            # Główny wiersz serii
            set_title = f"Seria #{len(dataset) - index + 1} — {meta['date']}"
            set_summary = f"Lokalizacja: {meta['location']} | Czas: {dur_str}"
            set_stats = f"Suma: {meta['total']} (OK: {meta['correct']} | Błędy: {meta['faulty']})"

            set_node = QTreeWidgetItem(self.tree, [set_title, set_summary, set_stats])
            set_node.setForeground(0, Qt.GlobalColor.cyan)

            # Wprowadzanie powtórzeń jako dzieci węzła serii
            for idx, rep in enumerate(set_data["repetitions"], 1):
                speed, status, shallow, far, tempo = rep

                rep_title = f"  ↳ Powtórzenie {idx}"
                rep_val = f"Czas trwania: {speed}s"

                # Zbieranie błędów w tekst
                errors = []
                if shallow:
                    errors.append("Za płytko")
                if far:
                    errors.append("Za daleko krzesła")
                if tempo:
                    errors.append("Brak tempa")
                errors_str = ", ".join(errors) if errors else "Brak błędu"

                rep_node = QTreeWidgetItem(set_node, [rep_title, rep_val, errors_str])

                # Kolorowanie statusu powtórzenia
                if status == "Correct":
                    rep_node.setForeground(1, Qt.GlobalColor.green)
                else:
                    rep_node.setForeground(1, Qt.GlobalColor.red)
                    rep_node.setForeground(2, rgba_color := Qt.GlobalColor.yellow)

            # Automatycznie rozwiń najnowszą serię
            if index == 1:
                set_node.setExpanded(True)
