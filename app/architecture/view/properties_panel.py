"""
PropertiesPanel — правая панель свойств выбранного элемента.

В M0 — пустая. show_element() появится в M1.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
    QFrame,
)


class PropertiesPanel(QWidget):
    """Правая панель: свойства выбранного элемента."""

    WIDTH = 260

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedWidth(self.WIDTH)
        self._build_ui()
        self.show_empty()

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

        self._body = QLabel("")
        self._body.setWordWrap(True)
        self._body.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._body.setStyleSheet(
            "color: #5A5F68; font-size: 10px; padding-top: 8px;"
        )
        layout.addWidget(self._body)

        layout.addStretch()

    # ------------------------------------------------------------

    def show_empty(self) -> None:
        """Ничего не выбрано."""
        self._body.setText("Ничего не выбрано.")

    def show_element(self, element) -> None:
        """Показать свойства элемента.

        В M0 не используется — заготовка для M1.
        """
        self._body.setText(
            f"Тип: {getattr(element, 'type', '?')}\n"
            f"ID: {getattr(element, 'id', '?')}"
        )
