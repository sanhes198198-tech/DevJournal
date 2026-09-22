"""
AutoRuleDialog — настройка правила авто-размножения точек.

Пользователь выбирает группу с одной extra-точкой (шаблон),
задаёт ось, направление, шаг и группу-границу. После OK —
правило сохраняется в group.auto_rule, движок пересчитывает точки.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class AutoRuleDialog(QDialog):
    """Диалог правила авто-размножения для одной группы."""

    def __init__(
        self,
        group,
        all_groups: list,
        parent=None,
    ):
        super().__init__(parent)

        self._group = group
        self._all_groups = list(all_groups)

        # result_rule = dict или None (если удалить)
        self.result_rule: dict | None = None

        self.setWindowTitle("Правило размножения точек")
        self.resize(440, 520)

        self._build_ui()
        self._load_existing()

    # ------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(f"Группа: {self._group.label}")
        title.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(title)

        hint = QLabel(
            "Шаблон-точка будет дублироваться вдоль выбранной оси\n"
            "с заданным шагом, пока не дойдёт до группы-границы."
        )
        hint.setStyleSheet(
            "color: #858B93; font-size: 11px; padding-bottom: 4px;"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(8)

        self._axis_combo = QComboBox()
        self._axis_combo.addItem("Y (вертикаль)", "y")
        self._axis_combo.addItem("X (горизонталь)", "x")
        self._axis_combo.currentIndexChanged.connect(
            self._on_axis_changed
        )
        form.addRow("Ось:", self._axis_combo)

        self._dir_combo = QComboBox()
        self._dir_combo.addItem("Вверх / Влево (−)", -1)
        self._dir_combo.addItem("Вниз / Вправо (+)", +1)
        form.addRow("Направление:", self._dir_combo)

        self._step_spin = QDoubleSpinBox()
        self._step_spin.setRange(0.001, 10000.0)
        self._step_spin.setDecimals(3)
        self._step_spin.setSingleStep(0.1)
        self._step_spin.setValue(3.0)
        self._step_spin.setSuffix(" м")
        form.addRow("Шаг:", self._step_spin)

        self._until_combo = QComboBox()
        self._until_combo.addItem("— без границы —", "")
        for g in self._all_groups:
            if g.id == self._group.id:
                continue
            self._until_combo.addItem(
                f"{g.label}  ({g.name})", g.name,
            )
        form.addRow("До группы:", self._until_combo)

        layout.addLayout(form)

        # V15: вторая ось (сетка точек)
        self._axis2_check = QCheckBox(
            "Размножать и по второй оси (сетка)"
        )
        self._axis2_check.setChecked(False)
        layout.addWidget(self._axis2_check)

        self._axis2_container = QWidget()
        form2 = QFormLayout(self._axis2_container)
        form2.setSpacing(8)
        form2.setContentsMargins(0, 0, 0, 0)

        self._axis2_combo = QComboBox()
        self._axis2_combo.addItem("X (горизонталь)", "x")
        self._axis2_combo.addItem("Y (вертикаль)", "y")
        form2.addRow("Ось 2:", self._axis2_combo)

        self._dir2_combo = QComboBox()
        self._dir2_combo.addItem("Влево / Вверх (−)", -1)
        self._dir2_combo.addItem("Вправо / Вниз (+)", +1)
        form2.addRow("Направление 2:", self._dir2_combo)

        self._step2_spin = QDoubleSpinBox()
        self._step2_spin.setRange(0.001, 10000.0)
        self._step2_spin.setDecimals(3)
        self._step2_spin.setSingleStep(0.1)
        self._step2_spin.setValue(2.0)
        self._step2_spin.setSuffix(" м")
        form2.addRow("Шаг 2:", self._step2_spin)

        self._until2_combo = QComboBox()
        self._until2_combo.addItem("— без границы —", "")
        for g in self._all_groups:
            if g.id == self._group.id:
                continue
            self._until2_combo.addItem(
                f"{g.label}  ({g.name})", g.name,
            )
        form2.addRow("До группы 2:", self._until2_combo)

        layout.addWidget(self._axis2_container)
        self._axis2_container.setVisible(False)

        self._axis2_check.toggled.connect(
            self._axis2_container.setVisible
        )

        layout.addStretch()

        # Нижний ряд: слева «Удалить правило» (если есть), справа OK/Cancel
        bottom = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        bottom.button(QDialogButtonBox.StandardButton.Ok).setText(
            "Сохранить"
        )
        bottom.button(QDialogButtonBox.StandardButton.Cancel).setText(
            "Отмена"
        )
        bottom.accepted.connect(self._on_accept)
        bottom.rejected.connect(self.reject)

        self._btn_remove = QPushButton("Удалить правило")
        self._btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_remove.clicked.connect(self._on_remove)
        bottom.addButton(
            self._btn_remove,
            QDialogButtonBox.ButtonRole.DestructiveRole,
        )

        layout.addWidget(bottom)

    # ------------------------------------------------------------

    def _on_axis_changed(self, idx: int) -> None:
        axis = self._axis_combo.currentData()
        self._dir_combo.clear()
        if axis == "y":
            self._dir_combo.addItem("Вверх (−)", -1)
            self._dir_combo.addItem("Вниз (+)", +1)
        else:
            self._dir_combo.addItem("Влево (−)", -1)
            self._dir_combo.addItem("Вправо (+)", +1)

    # ------------------------------------------------------------

    def _load_existing(self) -> None:
        rule = getattr(self._group, "auto_rule", None)
        if not rule:
            self._btn_remove.setEnabled(False)
            # По умолчанию: Y вверх
            self._axis_combo.setCurrentIndex(0)
            self._dir_combo.setCurrentIndex(0)
            return

        axis = rule.get("axis", "y")
        step = float(rule.get("step", 3.0))
        until = rule.get("until_group", "")

        idx = self._axis_combo.findData(axis)
        if idx >= 0:
            self._axis_combo.setCurrentIndex(idx)

        # Направление по знаку step
        dir_val = -1 if step < 0 else +1
        idx = self._dir_combo.findData(dir_val)
        if idx >= 0:
            self._dir_combo.setCurrentIndex(idx)

        self._step_spin.setValue(abs(step))

        if until:
            idx = self._until_combo.findData(until)
            if idx >= 0:
                self._until_combo.setCurrentIndex(idx)

        # V15: вторая ось
        axis_x = rule.get("axis_x") or ""
        if axis_x:
            self._axis2_check.setChecked(True)
            idx = self._axis2_combo.findData(axis_x)
            if idx >= 0:
                self._axis2_combo.setCurrentIndex(idx)
            step_x = float(rule.get("step_x", 2.0))
            dir_x = -1 if step_x < 0 else +1
            idx = self._dir2_combo.findData(dir_x)
            if idx >= 0:
                self._dir2_combo.setCurrentIndex(idx)
            self._step2_spin.setValue(abs(step_x))
            until_x = rule.get("until_group_x") or ""
            if until_x:
                idx = self._until2_combo.findData(until_x)
                if idx >= 0:
                    self._until2_combo.setCurrentIndex(idx)

    # ------------------------------------------------------------

    def _on_remove(self) -> None:
        self.result_rule = None
        self.accept()

    def _on_accept(self) -> None:
        axis = self._axis_combo.currentData()
        dir_val = self._dir_combo.currentData() or -1
        step_abs = float(self._step_spin.value())
        until = self._until_combo.currentData() or ""

        if step_abs <= 0:
            self._step_spin.setFocus()
            return

        step = step_abs * dir_val

        rule = {
            "axis": axis,
            "step": step,
            "until_group": until,
            "skip_groups": [],
        }

        # V15: вторая ось (если включена)
        if self._axis2_check.isChecked():
            axis2 = self._axis2_combo.currentData()
            dir2 = self._dir2_combo.currentData() or -1
            step2_abs = float(self._step2_spin.value())
            until2 = self._until2_combo.currentData() or ""
            if step2_abs > 0 and axis2:
                rule["axis_x"] = axis2
                rule["step_x"] = step2_abs * dir2
                rule["until_group_x"] = until2

        self.result_rule = rule
        self.accept()