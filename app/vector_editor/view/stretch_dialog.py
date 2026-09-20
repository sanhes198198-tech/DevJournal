"""
StretchDialog — мастер параметра-растяжения.

Спрашивает:
  - имя параметра
  - группу «стоит» (не двигается)
  - группу «тянется» (едет на всю Δ по оси)
  - группу «вторая сторона» (едет на -Δ, симметрично)
  - ось движения: ↑ Вверх / ↔ Вправо / ↔ Влево
  - группу «середина» (едет на Δ/2 — опционально)
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class StretchDialog(QDialog):
    """Мастер параметра-растяжения."""

    def __init__(self, asset, parent=None):
        super().__init__(parent)

        self._asset = asset
        self.result_name: str = "height"
        self.result_label: str = "Высота"
        self.result_bottom_id: str | None = None
        self.result_top_id: str | None = None
        self.result_second_id: str | None = None
        self.result_middle_id: str | None = None
        self.result_axis: str = "y"   # "y" | "x+1" | "x-1"

        self.setWindowTitle("Растяжка")
        self.resize(500, 400)

        self._build_ui()
        self._refresh_combos()

    # ------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Создать параметр растяжения")
        title.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(title)

        hint = QLabel(
            "Стоит — не двигается.\n"
            "Тянется — едет на всю Δ.\n"
            "Вторая сторона — едет на -Δ (симметрично).\n"
            "Середина — растягивается на Δ/2."
        )
        hint.setStyleSheet("color: #858B93; font-size: 11px;")
        layout.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(8)

        self._name_edit = QLineEdit("height")
        form.addRow("Имя (slug):", self._name_edit)

        self._label_edit = QLineEdit("Высота")
        form.addRow("Название:", self._label_edit)

        self._axis_combo = QComboBox()
        self._axis_combo.addItem("↑ Вверх (Y)", "y")
        self._axis_combo.addItem("↔ Вправо (X)", "x+1")
        self._axis_combo.addItem("↔ Влево (X)", "x-1")
        form.addRow("Ось:", self._axis_combo)

        self._bottom_combo = QComboBox()
        form.addRow("Стоит:", self._bottom_combo)

        self._top_combo = QComboBox()
        form.addRow("Тянется:", self._top_combo)

        self._second_combo = QComboBox()
        form.addRow("Вторая сторона:", self._second_combo)

        self._middle_combo = QComboBox()
        form.addRow("Середина:", self._middle_combo)

        layout.addLayout(form)
        layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Создать")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add_groups_to_combo(self, combo, empty_text):
        combo.clear()
        combo.addItem(empty_text, None)
        for g in sorted(
            self._asset.semantic_groups.values(),
            key=lambda x: (x.label or x.name).lower(),
        ):
            combo.addItem(f"{g.label}  ({g.name})", g.id)

    def _refresh_combos(self) -> None:
        self._add_groups_to_combo(self._bottom_combo, "— не выбрано —")
        self._add_groups_to_combo(self._top_combo, "— не выбрано —")
        self._add_groups_to_combo(self._second_combo, "— нет —")
        self._add_groups_to_combo(self._middle_combo, "— нет —")

        # Автоподстановка
        for i in range(self._bottom_combo.count()):
            gid = self._bottom_combo.itemData(i)
            g = self._asset.get_semantic_group(gid) if gid else None
            if g and g.name in ("foundation", "bottom", "left"):
                self._bottom_combo.setCurrentIndex(i)
                break

        for i in range(self._top_combo.count()):
            gid = self._top_combo.itemData(i)
            g = self._asset.get_semantic_group(gid) if gid else None
            if g and g.name in ("top", "right"):
                self._top_combo.setCurrentIndex(i)
                break

        for i in range(self._middle_combo.count()):
            gid = self._middle_combo.itemData(i)
            g = self._asset.get_semantic_group(gid) if gid else None
            if g and g.name in ("facade", "middle"):
                self._middle_combo.setCurrentIndex(i)
                break

    # ------------------------------------------------------------

    def _on_accept(self) -> None:
        name = self._name_edit.text().strip()
        label = self._label_edit.text().strip()

        if not name or not label:
            return

        self.result_axis = self._axis_combo.currentData() or "y"
        self.result_bottom_id = self._bottom_combo.currentData()
        self.result_top_id = self._top_combo.currentData()
        self.result_second_id = self._second_combo.currentData()
        self.result_middle_id = self._middle_combo.currentData()

        if not self.result_top_id:
            return

        if self.result_top_id == self.result_second_id:
            self.result_second_id = None
        if self.result_top_id == self.result_middle_id:
            self.result_middle_id = None

        self.result_name = name
        self.result_label = label
        self.accept()
