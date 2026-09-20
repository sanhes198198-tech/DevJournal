"""
PropertiesPanel — правая панель свойств Component'а.

Показывает X / Y / Поворот / Масштаб выбранного компонента.
Изменение → сигнал value_changed(comp_id, field, value).
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFrame,
)


class PropertiesPanel(QWidget):
    """Правая панель свойств."""

    # (comp_id, field, value) — field: "x" / "y" / "rotation" / "scale"
    value_changed = Signal(str, str, float)
    # comp_id — удалить компонент
    delete_requested = Signal(str)

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
        self._btn_delete.setEnabled(enabled)

    # ------------------------------------------------------------

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
