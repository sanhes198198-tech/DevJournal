"""
ScaleDialog — пропорциональное масштабирование контура.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)


class ScaleDialog(QDialog):
    """Задаёт целевой размер W×H для контура."""

    def __init__(
        self, current_w: float, current_h: float, parent=None,
    ):
        super().__init__(parent)

        self._current_w = max(current_w, 1e-6)
        self._current_h = max(current_h, 1e-6)
        self._muted = False

        self.setWindowTitle("Масштабировать контур")
        self.resize(360, 220)

        self.result_w: float = self._current_w
        self.result_h: float = self._current_h

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        info = QLabel(
            f"Текущий размер: {self._current_w:.3f} × "
            f"{self._current_h:.3f} м"
        )
        info.setStyleSheet(
            "color: #E5E5E5; font-size: 12px; padding-bottom: 4px;"
        )
        layout.addWidget(info)

        form = QFormLayout()
        form.setSpacing(8)

        self._w_spin = QDoubleSpinBox()
        self._w_spin.setRange(0.001, 10000)
        self._w_spin.setDecimals(3)
        self._w_spin.setSingleStep(0.1)
        self._w_spin.setValue(self._current_w)
        self._w_spin.valueChanged.connect(self._on_w_changed)
        form.addRow("Ширина W, м:", self._w_spin)

        self._h_spin = QDoubleSpinBox()
        self._h_spin.setRange(0.001, 10000)
        self._h_spin.setDecimals(3)
        self._h_spin.setSingleStep(0.1)
        self._h_spin.setValue(self._current_h)
        self._h_spin.valueChanged.connect(self._on_h_changed)
        form.addRow("Высота H, м:", self._h_spin)

        layout.addLayout(form)

        self._keep_ratio = QCheckBox("Сохранять пропорции")
        self._keep_ratio.setChecked(True)
        layout.addWidget(self._keep_ratio)

        layout.addStretch()

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText(
            "Масштабировать"
        )
        btns.button(QDialogButtonBox.StandardButton.Cancel).setText(
            "Отмена"
        )
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_w_changed(self, val: float) -> None:
        if self._muted or not self._keep_ratio.isChecked():
            return
        ratio = self._current_h / self._current_w
        new_h = val * ratio
        self._muted = True
        self._h_spin.setValue(new_h)
        self._muted = False

    def _on_h_changed(self, val: float) -> None:
        if self._muted or not self._keep_ratio.isChecked():
            return
        ratio = self._current_w / self._current_h
        new_w = val * ratio
        self._muted = True
        self._w_spin.setValue(new_w)
        self._muted = False

    def _on_ok(self) -> None:
        self.result_w = self._w_spin.value()
        self.result_h = self._h_spin.value()
        self.accept()