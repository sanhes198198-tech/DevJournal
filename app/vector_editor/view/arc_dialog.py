"""
ArcDialog — настройка кривизны одного ребра.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
    QPushButton, QSlider, QVBoxLayout,
)


class ArcDialog(QDialog):
    """Диалог настройки кривизны ребра."""

    value_changed = Signal(float)

    def __init__(self, current: float = 0.0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Изогнуть ребро")
        self.resize(420, 140)

        self._value = float(current)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        hint = QLabel(
            "Ползунок: -1 .. +1. Ноль — прямой отрезок.\n"
            "Знак определяет сторону изгиба."
        )
        hint.setStyleSheet("color: #858B93; font-size: 11px;")
        layout.addWidget(hint)

        # Ползунок
        row = QHBoxLayout()
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(-100, 100)
        self._slider.setValue(int(self._value * 100))
        self._slider.valueChanged.connect(self._on_slider)
        row.addWidget(self._slider, 1)

        self._label = QLabel(f"{self._value:+.2f}")
        self._label.setFixedWidth(60)
        self._label.setAlignment(Qt.AlignmentFlag.AlignRight)
        row.addWidget(self._label)
        layout.addLayout(row)

        layout.addStretch()

        # Кнопки
        btns = QHBoxLayout()

        btn_reset = QPushButton("Прямая (0)")
        btn_reset.clicked.connect(self._on_reset)
        btns.addWidget(btn_reset)

        btns.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Применить")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        btns.addWidget(buttons)

        layout.addLayout(btns)

    def _on_slider(self, v: int) -> None:
        self._value = v / 100.0
        self._label.setText(f"{self._value:+.2f}")
        self.value_changed.emit(self._value)

    def _on_reset(self) -> None:
        self._slider.setValue(0)

    def value(self) -> float:
        return self._value