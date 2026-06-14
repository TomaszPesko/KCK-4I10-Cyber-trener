from PySide6.QtCore import QDateTime, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
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
