from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QBrush, QColor, QTextDocument
from PySide6.QtWidgets import (
    QHeaderView,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTreeWidget,
    QTreeWidgetItem,
)


class WrappingHTMLDelegate(QStyledItemDelegate):
    """Zaawansowany delegat wykorzystujący silnik QTextDocument do wymuszenia

    pełnego autowrapingu tekstów w kolumnach tabeli Qt.
    """

    def sizeHint(self, option, index):
        doc = QTextDocument()
        doc.setHtml(index.data())

        # Pobieramy szerokość kolumny z widgetu nadrzędnego
        tree_widget = index.model().parent()
        if tree_widget:
            column_width = tree_widget.columnWidth(index.column())
            doc.setTextWidth(column_width - 10)  # Margines bezpieczeństwa na padding

        return QSize(
            doc.idealWidth(), doc.size().height() + 12
        )  # Dodatkowy padding w pionie


class TrainingDataHistoryWidget(QTreeWidget):
    """Widget wyświetlający załadowane serie historyczne i zagnieżdżone powtórzenia w strukturze drzewa."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHeaderLabels(
            ["Parametr / Powtórzenie", "Status / Wartość", "Wykryte błędy"]
        )

        # Konfiguracja nagłówków zapobiegająca ignorowaniu rozmiarów pionowych
        self.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.header().setSectionResizeMode(
            2, QHeaderView.Interactive
        )  # Pozwala na elastyczny resize
        self.header().resizeSection(2, 300)  # Sugerowana szerokość startowa dla błędów

        # 1. Włączamy natywne właściwości zawijania na poziomie widoku drzewiastego
        self.setWordWrap(True)
        self.setUniformRowHeights(
            False
        )  # KLUCZOWE: Każdy wiersz może mieć teraz inną wysokość!

        # 2. Podpinamy zaawansowany delegat pod kolumnę z błędami
        self.setItemDelegateForColumn(2, WrappingHTMLDelegate(self))

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
        """Dynamicznie buduje drzewo historii na podstawie struktury bazy danych lub cache."""
        self.clear()

        if not cached_sets_data:
            return

        if isinstance(cached_sets_data, dict):
            incoming_sets = [cached_sets_data]
        elif isinstance(cached_sets_data, list):
            incoming_sets = cached_sets_data
        else:
            incoming_sets = [cached_sets_data]

        try:
            sorted_sets = sorted(
                incoming_sets,
                key=lambda x: x["metadata"]["date"] if isinstance(x, dict) else x[1],
                reverse=True,
            )
        except Exception:
            sorted_sets = incoming_sets

        for row in sorted_sets:
            if isinstance(row, dict):
                meta = row.get("metadata", {})
                exec_date = meta.get("date", "Nieznana data")
                location = meta.get("location", "Dom")
                duration = meta.get("duration", 0)
                correct_reps = meta.get("correct", 0)
                total_reps = meta.get("total", 0)
                reps_list = row.get("repetitions", [])
            else:
                exec_date = row[1]
                location = row[2]
                duration = row[3]
                total_reps = row[4]
                correct_reps = row[5]
                reps_list = row[7] if len(row) > 7 else []

            set_item = QTreeWidgetItem(self)
            set_item.setText(0, f"🏋️ Seria — {exec_date}")
            set_item.setText(1, f"Lokalizacja: {location}")
            set_item.setText(2, f"Powtórzenia: {correct_reps}/{total_reps}")
            set_item.setForeground(0, QBrush(QColor("#00cc66")))

            dur_item = QTreeWidgetItem(set_item)
            dur_item.setText(0, " ⏱ Czas trwania")
            dur_item.setText(1, f"{duration} sek.")

            if not reps_list:
                continue

            for r_idx, rep in enumerate(reps_list):
                rep_item = QTreeWidgetItem(set_item)
                rep_item.setText(0, f"   ↳ Powtórzenie {r_idx + 1}")

                speed = 2.2
                too_shallow = False
                too_far = False
                lacks_tempo = False

                if isinstance(rep, dict):
                    speed = rep.get("speed", 2.2)
                    errors = rep.get("errors", {})
                    too_shallow = bool(errors.get("legs_bent", False)) or bool(
                        errors.get("too_shallow", False)
                    )
                    too_far = (
                        bool(errors.get("too_narrow", False))
                        or bool(errors.get("too_wide", False))
                        or bool(errors.get("too_far_from_chair", False))
                    )
                    lacks_tempo = bool(errors.get("bad_torso_angle", False)) or bool(
                        errors.get("lacks_tempo_control", False)
                    )
                else:
                    length = len(rep)
                    if length == 5:
                        speed = rep[0]
                        too_shallow = bool(rep[2])
                        too_far = bool(rep[3])
                        lacks_tempo = bool(rep[4])
                    elif length >= 7:
                        speed = rep[2]
                        too_shallow = bool(rep[4])
                        too_far = bool(rep[5])
                        lacks_tempo = bool(rep[6])
                    else:
                        speed = rep[0] if length > 0 else 2.2
                        too_shallow = bool(rep[1]) if length > 1 else False

                is_faulty = too_shallow or too_far or lacks_tempo
                status_text = "Z błędami" if is_faulty else "Poprawne"
                rep_item.setText(1, f"Status: {status_text} ({speed}s)")

                active_errors = []
                if too_shallow:
                    active_errors.append("za płytko")
                if too_far:
                    active_errors.append("za daleko od krzesła")
                if lacks_tempo:
                    active_errors.append("brak kontroli tempa")

                if not is_faulty:
                    rep_item.setForeground(1, QBrush(QColor("#00cc66")))
                    rep_item.setText(2, "Brak uwag")
                    rep_item.setForeground(2, QBrush(QColor("#00cc66")))
                else:
                    rep_item.setForeground(1, QBrush(QColor("#ff3333")))

                    error_string = ", ".join(active_errors)
                    rep_item.setText(2, error_string)
                    rep_item.setForeground(2, QBrush(QColor("#ffaa00")))

        # Po załadowaniu wszystkich danych, zmuszamy drzewo do przeliczenia geometrii klatek
        self.doItemsLayout()
