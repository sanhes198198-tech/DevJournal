"""
ParametersPanel — правая нижняя панель со списком параметров Asset'а.

Клик по параметру → QDoubleSpinBox показывает его value.
Изменение spinbox → сигнал value_changed(param_id, new, old).
Editor слушает сигнал и применяет delta к геометрии.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QDoubleSpinBox,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QFrame,
    QMessageBox,
    QToolButton,
)

from .parameter_dialog import ParameterDialog


class ParametersPanel(QWidget):
    """Панель параметров."""

    # param_id, new_value, old_value
    value_changed = Signal(str, float, float)
    parameters_changed = Signal()
    # Клик по параметру в списке: param_id (или "" при снятии)
    parameter_selected = Signal(str)

    WIDTH = 260

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedWidth(self.WIDTH)

        self._asset = None
        self._selected_param_id: str | None = None
        self._last_value: float = 0.0
        self._muted = False   # блокировать эмиты при программном обновлении

        self._build_ui()

    # ------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Параметры")
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

        self._list = QListWidget()
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._list.setStyleSheet(
            "QListWidget { background: #181A1E; color: #E5E5E5; "
            "border: 1px solid #2A2D33; border-radius: 3px; "
            "font-size: 11px; }"
            "QListWidget::item { padding: 6px 8px; }"
            "QListWidget::item:selected { background: #2A2D33; }"
            "QListWidget::item:hover { background: #22262C; }"
        )
        layout.addWidget(self._list, 1)

        # Значение выбранного параметра
        value_row = QHBoxLayout()
        value_row.setContentsMargins(0, 0, 0, 0)
        value_row.setSpacing(6)

        lbl = QLabel("Значение:")
        lbl.setStyleSheet("color: #858B93; font-size: 10px;")
        value_row.addWidget(lbl)

        self._value_spin = QDoubleSpinBox()
        self._value_spin.setRange(-1e6, 1e6)
        self._value_spin.setDecimals(3)
        self._value_spin.setSingleStep(0.1)
        self._value_spin.setEnabled(False)
        self._value_spin.valueChanged.connect(self._on_spin_changed)
        value_row.addWidget(self._value_spin, 1)

        self._btn_reset = QToolButton()
        self._btn_reset.setText("↺")
        self._btn_reset.setToolTip("Сбросить значение к 0")
        self._btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_reset.setEnabled(False)
        self._btn_reset.clicked.connect(self._on_reset_value)
        self._style_button(self._btn_reset)
        value_row.addWidget(self._btn_reset)

        layout.addLayout(value_row)

        # Список таргетов выбранного параметра
        self._targets_label = QLabel("")
        self._targets_label.setStyleSheet(
            "color: #6B7280; font-size: 10px; padding: 2px 0 6px 0;"
        )
        self._targets_label.setWordWrap(True)
        layout.addWidget(self._targets_label)

        # Кнопки
        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(4)

        self._btn_add = QPushButton("+")
        self._btn_add.setToolTip("Создать параметр")
        self._btn_add.setFixedWidth(32)
        self._btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_add.clicked.connect(self._on_add)
        buttons.addWidget(self._btn_add)

        self._btn_edit = QPushButton("Изменить")
        self._btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_edit.clicked.connect(self._on_edit)
        buttons.addWidget(self._btn_edit, 1)

        self._btn_del = QPushButton("Удалить")
        self._btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_del.clicked.connect(self._on_delete)
        buttons.addWidget(self._btn_del)

        for b in (self._btn_add, self._btn_edit, self._btn_del):
            self._style_button(b)

        layout.addLayout(buttons)

    @staticmethod
    def _style_button(btn: QPushButton) -> None:
        btn.setStyleSheet(
            "QPushButton { background: #202328; color: #E5E5E5; "
            "border: 1px solid #2A2D33; border-radius: 3px; "
            "padding: 5px 8px; font-size: 11px; }"
            "QPushButton:hover { background: #2A2D33; }"
            "QPushButton:disabled { color: #5A5F68; }"
        )

    # ------------------------------------------------------------

    def set_asset(self, asset) -> None:
        self._asset = asset
        self._selected_param_id = None
        self._last_value = 0.0
        self.refresh()

    def refresh(self) -> None:
        self._muted = True
        self._list.clear()

        if self._asset is None:
            placeholder = QListWidgetItem("— нет Asset'а —")
            placeholder.setFlags(
                placeholder.flags() & ~Qt.ItemFlag.ItemIsSelectable
            )
            self._list.addItem(placeholder)
            self._reset_value_spin()
            self._targets_label.setText("")
            self._update_buttons()
            self._muted = False
            return

        params = self._asset.parameters_list()
        if not params:
            placeholder = QListWidgetItem("— нет параметров —")
            placeholder.setFlags(
                placeholder.flags() & ~Qt.ItemFlag.ItemIsSelectable
            )
            self._list.addItem(placeholder)
            self._reset_value_spin()
            self._targets_label.setText("")
            self._update_buttons()
            self._muted = False
            return

        for p in params:
            text = f"{p.label}  =  {p.value:g} {p.unit}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, p.id)
            self._list.addItem(item)

        # восстановить выбор, если он ещё валиден
        if self._selected_param_id is not None:
            for i in range(self._list.count()):
                it = self._list.item(i)
                if it.data(Qt.ItemDataRole.UserRole) == self._selected_param_id:
                    self._list.setCurrentItem(it)
                    p = self._asset.get_parameter(self._selected_param_id)
                    if p is not None:
                        self._set_value_spin(p.value, p.unit)
                        self._last_value = p.value
                    break
            else:
                self._selected_param_id = None
                self._reset_value_spin()

        self._refresh_targets_label()
        self._update_buttons()
        self._muted = False

    def _set_value_spin(self, value: float, unit: str) -> None:
        self._value_spin.setSuffix(f" {unit}")
        self._value_spin.setValue(value)
        self._value_spin.setEnabled(True)
        self._btn_reset.setEnabled(True)

    def _reset_value_spin(self) -> None:
        self._value_spin.setValue(0.0)
        self._value_spin.setSuffix("")
        self._value_spin.setEnabled(False)
        self._btn_reset.setEnabled(False)

    def _refresh_targets_label(self) -> None:
        """Показать таргеты выбранного параметра в виде текста."""
        if (
            self._asset is None
            or self._selected_param_id is None
        ):
            self._targets_label.setText("")
            return

        p = self._asset.get_parameter(self._selected_param_id)
        if p is None or not p.targets:
            self._targets_label.setText("→ нет привязок")
            return

        parts = []
        for t in p.targets:
            g = self._asset.get_semantic_group(t.group_id)
            gname = g.label if g else f"?{t.group_id}"
            # Компактно: знак + ось + коэф
            kx = t.koef_x
            ky = t.koef_y
            kparts = []
            if abs(kx) > 1e-9:
                kparts.append(f"{kx:+.2f}X")
            if abs(ky) > 1e-9:
                kparts.append(f"{ky:+.2f}Y")
            koef = " ".join(kparts) if kparts else "0"
            parts.append(f"{gname} ({koef})")

        self._targets_label.setText("→ " + ", ".join(parts))

    def _update_buttons(self) -> None:
        has_asset = self._asset is not None
        has_params = has_asset and self._asset.parameter_count() > 0
        has_selection = self._list.currentItem() is not None

        self._btn_add.setEnabled(has_asset)
        self._btn_edit.setEnabled(has_params and has_selection)
        self._btn_del.setEnabled(has_params and has_selection)

    # ------------------------------------------------------------

    def clear_selection(self) -> None:
        self._list.clearSelection()
        self._selected_param_id = None
        self._reset_value_spin()
        self._targets_label.setText("")
        self._update_buttons()
        self.parameter_selected.emit("")

    def _current_param_id(self) -> str | None:
        item = self._list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        if self._asset is None:
            return

        pid = item.data(Qt.ItemDataRole.UserRole)
        if not pid:
            return

        p = self._asset.get_parameter(pid)
        if p is None:
            return

        self._selected_param_id = pid
        self._muted = True
        self._set_value_spin(p.value, p.unit)
        self._last_value = p.value
        self._muted = False
        self._refresh_targets_label()
        self._update_buttons()

        self.parameter_selected.emit(pid)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        self._on_edit()

    # ------------------------------------------------------------

    def _on_reset_value(self) -> None:
        """Сбросить значение выбранного параметра к 0."""
        if self._selected_param_id is None or self._asset is None:
            return
        if not self._value_spin.isEnabled():
            return

        current = self._value_spin.value()
        if abs(current) < 1e-12:
            return

        # Программно выставляем — valueChanged сработает через
        # обычный механизм, применяя delta к геометрии
        self._value_spin.setValue(0.0)

    def _on_spin_changed(self, new_value: float) -> None:
        if self._muted:
            return
        if self._selected_param_id is None or self._asset is None:
            return

        old_value = self._last_value
        if abs(new_value - old_value) < 1e-12:
            return

        self._last_value = new_value
        self.value_changed.emit(
            self._selected_param_id, new_value, old_value,
        )
        # Обновляем строку списка
        self._update_current_item_text(new_value)

    def _update_current_item_text(self, value: float) -> None:
        if self._asset is None or self._selected_param_id is None:
            return
        p = self._asset.get_parameter(self._selected_param_id)
        if p is None:
            return
        item = self._list.currentItem()
        if item is None:
            return
        item.setText(f"{p.label}  =  {value:g} {p.unit}")

    # ------------------------------------------------------------

    def _on_add(self) -> None:
        if self._asset is None:
            return

        dlg = ParameterDialog(self._asset, parameter=None, parent=self)
        if dlg.exec() != ParameterDialog.DialogCode.Accepted:
            return
        if dlg.result_parameter is None:
            return

        self._asset.add_parameter(dlg.result_parameter)
        self.refresh()
        self.parameters_changed.emit()

    def _on_edit(self) -> None:
        if self._asset is None:
            return
        pid = self._current_param_id()
        if pid is None:
            return
        p = self._asset.get_parameter(pid)
        if p is None:
            return

        dlg = ParameterDialog(self._asset, parameter=p, parent=self)
        if dlg.exec() != ParameterDialog.DialogCode.Accepted:
            return

        self.refresh()
        self.parameters_changed.emit()

    def _on_delete(self) -> None:
        if self._asset is None:
            return
        pid = self._current_param_id()
        if pid is None:
            return
        p = self._asset.get_parameter(pid)
        if p is None:
            return

        reply = QMessageBox.question(
            self, "Удалить параметр",
            f"Удалить параметр «{p.label}»?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._asset.remove_parameter(pid)
        self._selected_param_id = None
        self.refresh()
        self.parameter_selected.emit("")
        self.parameters_changed.emit()
