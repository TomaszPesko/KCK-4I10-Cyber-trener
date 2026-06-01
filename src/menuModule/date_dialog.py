from PySide6.QtCore import QDate, QDateTime, Qt, QTime
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTimeEdit,
    QVBoxLayout,
)


class DateTimeDialog(QDialog):
    """Popup window providing separate date (calendar) and time selectors for workout sets."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ustaw datę i godzinę")
        self.setMinimumWidth(320)

        self.setStyleSheet("""
            QDialog { background-color: rgb(40, 40, 40); border: 2px solid #00cc66; border-radius: 10px; }
            QLabel { color: white; font-size: 14px; margin-top: 5px; }
            QDateEdit, QTimeEdit { 
                background-color: rgb(60, 60, 60); 
                color: white; 
                border: 1px solid #555; 
                border-radius: 5px; 
                padding: 6px; 
                font-size: 14px; 
            }
            QCalendarWidget QWidget { background-color: rgb(50, 50, 50); color: white; }
            QPushButton { background-color: rgba(60, 60, 60, 220); color: white; border-radius: 8px; padding: 8px; font-size: 13px; }
            QPushButton:hover { background-color: #00cc66; color: black; }
        """)

        layout = QVBoxLayout(self)

        # Sekcja Daty
        layout.addWidget(QLabel("Wybierz datę serii:"))
        self.date_edit = QDateEdit(self)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setCalendarPopup(True)  # Popup z kalendarzem
        layout.addWidget(self.date_edit)

        # Sekcja Godziny
        layout.addWidget(QLabel("Wybierz godzinę serii:"))
        self.time_edit = QTimeEdit(self)
        self.time_edit.setTime(QTime.currentTime())
        self.time_edit.setDisplayFormat("HH:mm:ss")
        self.time_edit.setCalendarPopup(True)  # Popup do wyboru czasu w PySide6
        layout.addWidget(self.time_edit)

        layout.addSpacing(15)

        btn_layout = QHBoxLayout()
        self.btn_confirm = QPushButton("Zatwierdź")
        self.btn_confirm.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Anuluj")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_confirm)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def get_date_string(self) -> str:
        """Combines picked date and time into expected database format."""
        date_part = self.date_edit.date().toString("yyyy-MM-dd")
        time_part = self.time_edit.time().toString("HH:mm:ss")
        return f"{date_part} {time_part}"
