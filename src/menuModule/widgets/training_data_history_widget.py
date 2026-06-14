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


class TrainingDataHistoryWidget(QTreeWidget):
    """Widget wyświetlający załadowane serie historyczne i zagnieżdżone powtórzenia w strukturze drzewa."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHeaderLabels(
            ["Parametr / Powtórzenie", "Status / Wartość", "Wykryte błędy"]
        )
        self.header().setSectionResizeMode(QHeaderView.Stretch)
        self.tree_set_dates = set()  # Pamięć podręczna dodanych dat

        # Stylizacja dopasowana do ciemnego motywu CyberTrenera
        self.setStyleSheet("""
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

    def populate_data(self, cached_sets_data):
        """Dynamicznie buduje drzewo historii na podstawie struktury z Twojej bazy danych."""
        self.clear()

        if not cached_sets_data:
            return

        # Standaryzacja: upewniamy się, że pracujemy na liście serii
        if isinstance(cached_sets_data, dict):
            incoming_sets = [cached_sets_data]
        elif isinstance(cached_sets_data, list):
            incoming_sets = cached_sets_data
        else:
            incoming_sets = [cached_sets_data]

        # Sortowanie chronologiczne serii (od najnowszych do najstarszych)
        try:
            sorted_sets = sorted(
                incoming_sets,
                key=lambda x: x["metadata"]["date"] if isinstance(x, dict) else x[1],
                reverse=True,
            )
        except Exception:
            sorted_sets = incoming_sets

        for row in sorted_sets:
            # 1. Odczyt metadanych serii w zależności od formatu (Słownik vs Krotka SQL)
            if isinstance(row, dict):
                meta = row.get("metadata", {})
                exec_date = meta.get("date", "Nieznana data")
                location = meta.get("location", "Dom")
                duration = meta.get("duration", 0)
                correct_reps = meta.get("correct", 0)
                total_reps = meta.get("total", 0)
                reps_list = row.get("repetitions", [])
            else:
                # Twoja oryginalna struktura krotki tabeli 'sets' z bazy danych SQLite:
                # row[0]=id, row[1]=execution_date, row[2]=location, row[3]=duration_seconds
                # row[4]=total_reps, row[5]=correct_reps, row[6]=faulty_reps, row[7]=lista_powtórzeń (opcjonalnie)
                exec_date = row[1]
                location = row[2]
                duration = row[3]
                total_reps = row[4]
                correct_reps = row[5]
                # Pobranie powtórzeń (zakładam, że są na końcu krotki lub jako kolejny element struktury)
                reps_list = row[7] if len(row) > 7 else []

            # Utworzenie nagłówka serii
            set_item = QTreeWidgetItem(self)
            set_item.setText(0, f"🏋️ Seria — {exec_date}")
            set_item.setText(1, f"Lokalizacja: {location}")
            set_item.setText(2, f"Powtórzenia: {correct_reps}/{total_reps}")
            set_item.setForeground(0, QBrush(QColor("#00cc66")))

            # Podwęzeł czasu trwania
            dur_item = QTreeWidgetItem(set_item)
            dur_item.setText(0, " ⏱ Czas trwania")
            dur_item.setText(1, f"{duration} sek.")

            # 2. Przetwarzanie i dodawanie powtórzeń do drzewa interfejsu
            if reps_list:
                for r_idx, rep in enumerate(reps_list):
                    rep_item = QTreeWidgetItem(set_item)
                    rep_item.setText(0, f"  ↳ Powtórzenie {r_idx + 1}")

                    # Definiujemy bezpieczne wartości domyślne
                    quality = "Correct"
                    speed = 2.0
                    too_shallow = False
                    too_far = False
                    lacks_tempo = False

                    if isinstance(rep, dict):
                        # Format słownikowy (Zasilany z JSON-a / Cache statystyk)
                        quality = rep.get("quality", "Correct")
                        speed = rep.get("speed", 2.0)
                        errors = rep.get("errors", {})
                        too_shallow = bool(errors.get("legs_bent", False))
                        too_far = bool(errors.get("too_narrow", False)) or bool(
                            errors.get("too_wide", False)
                        )
                        lacks_tempo = bool(errors.get("bad_torso_angle", False))
                    else:
                        # Format krotki (Surowy SQL) — DYNAMICZNA WERYFIKACJA DŁUGOŚCI (Bezpieczeństwo przed IndexError)
                        dlugosc = len(rep)

                        # Próbujemy mapować indeksy tylko wtedy, gdy fizycznie istnieją w krotce
                        if dlugosc > 2:
                            speed = rep[2]
                        if dlugosc > 3:
                            quality = rep[3]
                        if dlugosc > 4:
                            too_shallow = bool(rep[4])
                        if dlugosc > 5:
                            too_far = bool(rep[5])
                        if dlugosc > 6:
                            lacks_tempo = bool(rep[6])

                    # Ustawienie statusu i prędkości w GUI
                    rep_item.setText(1, f"Status: {quality} (Tempo: {speed}s)")

                    # Generowanie komunikatów o błędach w trzeciej kolumnie
                    active_errors = []
                    if too_shallow:
                        active_errors.append("za płytko")
                    if too_far:
                        active_errors.append("za daleko od krzesła")
                    if lacks_tempo:
                        active_errors.append("brak kontroli tempa")

                    if quality == "Correct":
                        rep_item.setForeground(1, QBrush(QColor("#00cc66")))
                        rep_item.setText(2, "Brak uwag")
                    else:
                        rep_item.setForeground(1, QBrush(QColor("#ff3333")))
                        rep_item.setText(
                            2,
                            (
                                ", ".join(active_errors)
                                if active_errors
                                else "Modyfikacja pozycji"
                            ),
                        )
                        rep_item.setForeground(2, QBrush(QColor("#ffaa00")))
