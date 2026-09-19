"""
PalettePanel — левая панель выбора архитектурных элементов.

В M0 — пустая. Наполнится в M1+ (Room, Wall, Window, Door, ...).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
    QFrame,
)


class PalettePanel(QWidget):
    """Левая панель: палитра элементов."""

    element_requested = Signal(str)   # type_name — для M1

    WIDTH = 200

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedWidth(self.WIDTH)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Элементы")
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

        placeholder = QLabel(
            "Палитра архитектурных элементов "
            "появится в следующих версиях."
        )
        placeholder.setWordWrap(True)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignTop)
        placeholder.setStyleSheet(
            "color: #5A5F68; font-size: 10px; padding-top: 8px;"
        )
        layout.addWidget(placeholder)

        layout.addStretch()
