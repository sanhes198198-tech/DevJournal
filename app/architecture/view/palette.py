"""
PalettePanel — левая панель выбора архитектурных элементов.

M1c: только «Комната». Wall/Window/Door — M2+.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFrame,
)


class PalettePanel(QWidget):
    """Левая панель: палитра элементов."""

    element_requested = Signal(str)   # type_name

    WIDTH = 200

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedWidth(self.WIDTH)
        self._build_ui()

    # ------------------------------------------------------------

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

        # --- Элементы палитры ---
        self._add_element_button(
            layout,
            label="+ Комната",
            tooltip="Нарисуйте прямоугольник на canvas",
            type_name="room",
        )

        layout.addStretch()

        hint = QLabel(
            "Стены, окна, двери — в следующих версиях."
        )
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignTop)
        hint.setStyleSheet(
            "color: #5A5F68; font-size: 10px; padding-top: 8px;"
        )
        layout.addWidget(hint)

    # ------------------------------------------------------------

    def _add_element_button(
        self,
        layout,
        label: str,
        tooltip: str,
        type_name: str,
    ) -> None:
        btn = QPushButton(label)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton {"
            "  background: #202328;"
            "  color: #E5E5E5;"
            "  border: 1px solid #2A2D33;"
            "  border-radius: 4px;"
            "  padding: 8px 12px;"
            "  text-align: left;"
            "  font-size: 12px;"
            "}"
            "QPushButton:hover {"
            "  background: #2A2D33;"
            "  border-color: #3A3F48;"
            "}"
            "QPushButton:pressed {"
            "  background: #1A1D22;"
            "}"
        )
        btn.clicked.connect(
            lambda _=False, tn=type_name: self.element_requested.emit(tn)
        )
        layout.addWidget(btn)
