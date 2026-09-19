"""
PropertiesPanel — правая панель свойств выделенного элемента.

M1d-2: только для Room. Универсальной системы для будущих
типов элементов нет намеренно.

Поведение:
  - Нет выделения  → «Ничего не выбрано»
  - Выделена Room  → поля Room
  - Изменение поля → signal field_changed(name, value)
  - preset_id      → read-only (только показ)
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..model.room import Room
from ..model.asset_instance import AssetInstance


class PropertiesPanel(QWidget):
    """Правая панель: свойства выделенного элемента."""

    field_changed = Signal(str, object)   # (field_name, new_value)

    WIDTH = 260

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedWidth(self.WIDTH)
        self._current_room: Room | None = None
        self._current_asset_instance: AssetInstance | None = None
        self._build_ui()

    # ============================================================
    # UI
    # ============================================================

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Свойства")
        title.setStyleSheet(
            "font-weight: 600; font-size: 12px; "
            "color: #E5E5E5; padding-bottom: 4px;"
        )
        layout.addWidget(title)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: #2A2D33;")
        layout.addWidget(line)

        self._stack = QStackedWidget()
        self._empty_page = self._build_empty_page()
        self._room_page = self._build_room_page()
        self._asset_page = self._build_asset_page()
        self._stack.addWidget(self._empty_page)
        self._stack.addWidget(self._room_page)
        self._stack.addWidget(self._asset_page)

        layout.addWidget(self._stack, 1)

    def _build_empty_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel("Ничего не выбрано.")
        label.setStyleSheet("color: #5A5F68; font-size: 11px;")
        label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        layout.addWidget(label)
        layout.addStretch()
        return page

    def _build_room_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # --- Название (выделенное поле) ---
        name_label = QLabel("Название")
        name_label.setStyleSheet(
            "color: #858B93; font-size: 10px;"
        )
        layout.addWidget(name_label)

        self._name_edit = QLineEdit()
        self._name_edit.setStyleSheet(_field_style())
        self._name_edit.editingFinished.connect(self._on_name_edited)
        layout.addWidget(self._name_edit)

        # --- Разделитель ---
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet("color: #2A2D33; margin: 4px 0;")
        layout.addWidget(sep)

        # --- Форма ---
        form = QFormLayout()
        form.setSpacing(6)
        form.setContentsMargins(0, 0, 0, 0)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._x_spin = self._make_float_spin(-10000.0, 10000.0)
        self._x_spin.valueChanged.connect(
            lambda v: self._emit("x", float(v))
        )
        form.addRow("X, м", self._x_spin)

        self._y_spin = self._make_float_spin(-10000.0, 10000.0)
        self._y_spin.valueChanged.connect(
            lambda v: self._emit("y", float(v))
        )
        form.addRow("Y, м", self._y_spin)

        self._w_spin = self._make_float_spin(0.1, 10000.0)
        self._w_spin.valueChanged.connect(
            lambda v: self._emit("width", float(v))
        )
        form.addRow("Ширина, м", self._w_spin)

        self._d_spin = self._make_float_spin(0.1, 10000.0)
        self._d_spin.valueChanged.connect(
            lambda v: self._emit("depth", float(v))
        )
        form.addRow("Глубина, м", self._d_spin)

        self._h_spin = self._make_float_spin(0.1, 10000.0)
        self._h_spin.valueChanged.connect(
            lambda v: self._emit("height", float(v))
        )
        form.addRow("Высота, м", self._h_spin)

        self._floor_spin = QSpinBox()
        self._floor_spin.setRange(-5, 100)
        self._floor_spin.setStyleSheet(_field_style())
        self._floor_spin.setKeyboardTracking(False)
        self._floor_spin.valueChanged.connect(
            lambda v: self._emit("floor", int(v))
        )
        form.addRow("Этаж", self._floor_spin)

        layout.addLayout(form)

        # --- Пресет (read-only) ---
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setFrameShadow(QFrame.Shadow.Sunken)
        sep2.setStyleSheet("color: #2A2D33; margin: 4px 0;")
        layout.addWidget(sep2)

        preset_label = QLabel("Пресет")
        preset_label.setStyleSheet(
            "color: #858B93; font-size: 10px;"
        )
        layout.addWidget(preset_label)

        self._preset_value = QLabel("—")
        self._preset_value.setStyleSheet(
            "color: #5A5F68; font-size: 11px; "
            "font-family: Consolas, monospace;"
        )
        layout.addWidget(self._preset_value)

        layout.addStretch()
        return page

    # ============================================================
    # PUBLIC API
    # ============================================================

    def show_empty(self) -> None:
        self._current_room = None
        self._current_asset_instance = None
        self._stack.setCurrentWidget(self._empty_page)

    def _build_asset_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        asset_label = QLabel("Ассет")
        asset_label.setStyleSheet("color: #858B93; font-size: 10px;")
        layout.addWidget(asset_label)

        self._asset_info = QLabel("—")
        self._asset_info.setStyleSheet(
            "color: #E5E5E5; font-size: 11px; "
            "font-family: Consolas, monospace;"
        )
        self._asset_info.setWordWrap(True)
        layout.addWidget(self._asset_info)

        self._asset_warning = QLabel("")
        self._asset_warning.setStyleSheet(
            "color: #D0021B; font-size: 10px; padding-top: 2px;"
        )
        self._asset_warning.setWordWrap(True)
        self._asset_warning.hide()
        layout.addWidget(self._asset_warning)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet("color: #2A2D33; margin: 4px 0;")
        layout.addWidget(sep)

        form = QFormLayout()
        form.setSpacing(6)
        form.setContentsMargins(0, 0, 0, 0)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._ai_x_spin = self._make_float_spin(-10000.0, 10000.0)
        self._ai_x_spin.valueChanged.connect(
            lambda v: self._emit("x", float(v))
        )
        form.addRow("X, м", self._ai_x_spin)

        self._ai_y_spin = self._make_float_spin(-10000.0, 10000.0)
        self._ai_y_spin.valueChanged.connect(
            lambda v: self._emit("y", float(v))
        )
        form.addRow("Y, м", self._ai_y_spin)

        self._ai_rot_spin = self._make_float_spin(-360.0, 360.0)
        self._ai_rot_spin.setSingleStep(5.0)
        self._ai_rot_spin.setKeyboardTracking(True)
        self._ai_rot_spin.setKeyboardTracking(True)
        self._ai_rot_spin.valueChanged.connect(
            lambda v: self._emit("rotation", float(v))
        )
        form.addRow("Поворот, °", self._ai_rot_spin)

        self._ai_scale_spin = self._make_float_spin(0.1, 10.0)
        self._ai_scale_spin.setDecimals(2)
        self._ai_scale_spin.setSingleStep(0.1)
        self._ai_scale_spin.setKeyboardTracking(True)
        self._ai_scale_spin.setKeyboardTracking(True)
        self._ai_scale_spin.valueChanged.connect(
            lambda v: self._emit("scale", float(v))
        )
        form.addRow("Масштаб", self._ai_scale_spin)

        self._ai_floor_spin = QSpinBox()
        self._ai_floor_spin.setRange(-5, 100)
        self._ai_floor_spin.setStyleSheet(_field_style())
        self._ai_floor_spin.setKeyboardTracking(False)
        self._ai_floor_spin.valueChanged.connect(
            lambda v: self._emit("floor", int(v))
        )
        form.addRow("Этаж", self._ai_floor_spin)

        layout.addLayout(form)
        layout.addStretch()
        return page

    def _show_asset_instance(self, instance) -> None:
        self._current_room = None
        self._current_asset_instance = instance

        self._set_signals_enabled(False)
        try:
            self._asset_info.setText(f"ID: {instance.asset_id}")
            self._asset_warning.hide()

            self._ai_x_spin.setValue(instance.x)
            self._ai_y_spin.setValue(instance.y)
            self._ai_rot_spin.setValue(instance.rotation)
            self._ai_scale_spin.setValue(instance.scale)
            self._ai_floor_spin.setValue(instance.floor)
        finally:
            self._set_signals_enabled(True)

        self._stack.setCurrentWidget(self._asset_page)

    def show_element(self, element) -> None:
        if isinstance(element, Room):
            self._show_room(element)
        elif isinstance(element, AssetInstance):
            self._show_asset_instance(element)
        else:
            self.show_empty()

    # ============================================================
    # INTERNAL
    # ============================================================

    def _show_room(self, room: Room) -> None:
        self._current_room = room

        # Блокируем сигналы на время заполнения
        self._set_signals_enabled(False)
        try:
            self._name_edit.setText(room.name)
            self._x_spin.setValue(room.x)
            self._y_spin.setValue(room.y)
            self._w_spin.setValue(room.width)
            self._d_spin.setValue(room.depth)
            self._h_spin.setValue(room.height)
            self._floor_spin.setValue(room.floor)
            self._preset_value.setText(room.preset_id or "—")
        finally:
            self._set_signals_enabled(True)

        self._stack.setCurrentWidget(self._room_page)

    def _emit(self, field: str, value) -> None:
        if self._current_room is None and self._current_asset_instance is None:
            return
        self.field_changed.emit(field, value)

    def _on_name_edited(self) -> None:
        if self._current_room is None:
            return
        new_name = self._name_edit.text().strip()
        if not new_name:
            # Пустое имя нельзя — откат
            self._name_edit.setText(self._current_room.name)
            return
        if new_name == self._current_room.name:
            return
        self.field_changed.emit("name", new_name)

    def _make_float_spin(self, lo: float, hi: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(lo, hi)
        spin.setDecimals(1)
        spin.setSingleStep(0.1)
        spin.setKeyboardTracking(False)
        spin.setStyleSheet(_field_style())
        return spin

    def _set_signals_enabled(self, enabled: bool) -> None:
        widgets = (
            self._name_edit,
            self._x_spin,
            self._y_spin,
            self._w_spin,
            self._d_spin,
            self._h_spin,
            self._floor_spin,
            self._ai_x_spin,
            self._ai_y_spin,
            self._ai_rot_spin,
            self._ai_scale_spin,
            self._ai_floor_spin,
        )
        for w in widgets:
            w.blockSignals(not enabled)


# ================================================================
# STYLE
# ================================================================

def _field_style() -> str:
    return (
        "QLineEdit, QDoubleSpinBox, QSpinBox {"
        "  background: #202328;"
        "  color: #E5E5E5;"
        "  border: 1px solid #2A2D33;"
        "  border-radius: 3px;"
        "  padding: 4px 6px;"
        "  font-size: 11px;"
        "}"
        "QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {"
        "  border-color: #4A5A6A;"
        "}"
        "QDoubleSpinBox::up-button, QSpinBox::up-button,"
        "QDoubleSpinBox::down-button, QSpinBox::down-button {"
        "  width: 14px;"
        "  background: #2A2D33;"
        "  border: none;"
        "}"
        "QDoubleSpinBox::up-button:hover, QSpinBox::up-button:hover,"
        "QDoubleSpinBox::down-button:hover, QSpinBox::down-button:hover {"
        "  background: #3A3F48;"
        "}"
    )
