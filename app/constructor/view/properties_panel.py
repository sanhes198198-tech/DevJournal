"""
PropertiesPanel — правая панель свойств Component'а.

Показывает X / Y / Поворот / Масштаб выбранного компонента.
Изменение → сигнал value_changed(comp_id, field, value).
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QSpinBox,
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QFrame,
)


class PropertiesPanel(QWidget):
    """Правая панель свойств."""

    # (comp_id, field, value) — field: "x" / "y" / "rotation" / "scale" / "layer"
    value_changed = Signal(str, str, float)
    # comp_id — удалить компонент
    delete_requested = Signal(str)
    # (comp_id, direction) — direction: +1 / -1
    layer_shift = Signal(str, int)
    # (comp_id, filled)
    filled_changed = Signal(str, bool)

    WIDTH = 260

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(self.WIDTH)

        self._current_comp = None
        self._muted = False

        self._build_ui()
        self.clear()

    # ------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Свойства")
        title.setStyleSheet(
            "font-weight: 600; font-size: 12px; color: #1A1A1A;"
        )
        layout.addWidget(title)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # Название выбранного
        self._name_label = QLabel("— не выбрано —")
        self._name_label.setStyleSheet(
            "color: #444444; font-size: 11px; padding: 4px 0;"
        )
        self._name_label.setWordWrap(True)
        layout.addWidget(self._name_label)

        # Спинбоксы
        form = QFormLayout()
        form.setSpacing(8)

        self._x_spin = QDoubleSpinBox()
        self._x_spin.setRange(-1000, 1000)
        self._x_spin.setDecimals(2)
        self._x_spin.setSingleStep(0.1)
        self._x_spin.valueChanged.connect(
            lambda v: self._emit("x", v)
        )
        form.addRow("X, м:", self._x_spin)

        self._y_spin = QDoubleSpinBox()
        self._y_spin.setRange(-1000, 1000)
        self._y_spin.setDecimals(2)
        self._y_spin.setSingleStep(0.1)
        self._y_spin.valueChanged.connect(
            lambda v: self._emit("y", v)
        )
        form.addRow("Y, м:", self._y_spin)

        self._rot_spin = QDoubleSpinBox()
        self._rot_spin.setRange(-360, 360)
        self._rot_spin.setDecimals(1)
        self._rot_spin.setSingleStep(15)
        self._rot_spin.valueChanged.connect(
            lambda v: self._emit("rotation", v)
        )
        form.addRow("Поворот, °:", self._rot_spin)

        self._scale_spin = QDoubleSpinBox()
        self._scale_spin.setRange(0.1, 100.0)
        self._scale_spin.setDecimals(3)
        self._scale_spin.setSingleStep(0.1)
        self._scale_spin.valueChanged.connect(
            lambda v: self._emit("scale", v)
        )
        form.addRow("Масштаб:", self._scale_spin)

        # Слой — со стрелками вверх/вниз
        layer_row = QHBoxLayout()
        self._layer_spin = QSpinBox()
        self._layer_spin.setRange(-100, 100)
        self._layer_spin.setValue(0)
        self._layer_spin.valueChanged.connect(
            lambda v: self._emit("layer", float(v))
        )
        layer_row.addWidget(self._layer_spin, 1)

        btn_up = QToolButton()
        btn_up.setText("▲")
        btn_up.setToolTip("Выше")
        btn_up.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_up.clicked.connect(
            lambda: self._shift_layer(+1)
        )
        layer_row.addWidget(btn_up)

        btn_down = QToolButton()
        btn_down.setText("▼")
        btn_down.setToolTip("Ниже")
        btn_down.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_down.clicked.connect(
            lambda: self._shift_layer(-1)
        )
        layer_row.addWidget(btn_down)

        self._btn_up = btn_up
        self._btn_down = btn_down
        form.addRow("Слой:", layer_row)

        self._filled_check = QCheckBox("Залить белым (перекрывать)")
        self._filled_check.toggled.connect(self._on_filled_toggled)
        form.addRow("", self._filled_check)

        layout.addLayout(form)
        layout.addStretch()

        # Кнопка удалить
        self._btn_delete = QPushButton("Удалить компонент")
        self._btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_delete.clicked.connect(self._on_delete)
        layout.addWidget(self._btn_delete)

    # ------------------------------------------------------------

    def clear(self) -> None:
        """Ничего не выбрано."""
        self._current_comp = None
        self._name_label.setText("— не выбрано —")
        self._muted = True
        self._x_spin.setValue(0.0)
        self._y_spin.setValue(0.0)
        self._rot_spin.setValue(0.0)
        self._scale_spin.setValue(1.0)
        self._layer_spin.setValue(0)
        self._filled_check.setChecked(False)
        self._muted = False
        self._set_enabled(False)

    def show_component(self, comp) -> None:
        """Показать свойства компонента."""
        self._current_comp = comp
        self._name_label.setText(comp.name or comp.id)
        self._muted = True
        self._x_spin.setValue(comp.x)
        self._y_spin.setValue(comp.y)
        self._rot_spin.setValue(comp.rotation)
        self._scale_spin.setValue(comp.scale)
        self._layer_spin.setValue(int(getattr(comp, "layer", 0)))
        self._filled_check.setChecked(
            bool(getattr(comp, "filled", False))
        )
        self._muted = False
        self._set_enabled(True)

    def update_values(self, x: float, y: float,
                      rotation: float, scale: float) -> None:
        """Обновить значения без эмита (после drag)."""
        if self._current_comp is None:
            return
        self._muted = True
        self._x_spin.setValue(x)
        self._y_spin.setValue(y)
        self._rot_spin.setValue(rotation)
        self._scale_spin.setValue(scale)
        self._muted = False

    def _set_enabled(self, enabled: bool) -> None:
        self._x_spin.setEnabled(enabled)
        self._y_spin.setEnabled(enabled)
        self._rot_spin.setEnabled(enabled)
        self._scale_spin.setEnabled(enabled)
        self._layer_spin.setEnabled(enabled)
        self._filled_check.setEnabled(enabled)
        self._btn_up.setEnabled(enabled)
        self._btn_down.setEnabled(enabled)
        self._btn_delete.setEnabled(enabled)

    # ------------------------------------------------------------

    def _on_filled_toggled(self, checked: bool) -> None:
        if self._muted or self._current_comp is None:
            return
        self.filled_changed.emit(self._current_comp.id, checked)

    def _shift_layer(self, direction: int) -> None:
        if self._current_comp is None:
            return
        self.layer_shift.emit(self._current_comp.id, direction)

    def _emit(self, field: str, value: float) -> None:
        if self._muted or self._current_comp is None:
            return
        self.value_changed.emit(
            self._current_comp.id, field, value,
        )

    def _on_delete(self) -> None:
        if self._current_comp is None:
            return
        self.delete_requested.emit(self._current_comp.id)
