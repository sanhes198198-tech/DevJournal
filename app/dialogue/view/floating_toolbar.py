"""
Плавающий мини-toolbar внизу справа на canvas.

Стиль: flat / thin / minimal. Иконки или короткий текст.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton


class FloatingToolbar(QFrame):
    """Плавающая панель быстрого доступа к частым действиям."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("dialogueFloatingToolbar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        self.btn_zoom_out = self._make_button(
            "-", "Уменьшить", 32
        )
        self.btn_zoom_in = self._make_button(
            "+", "Увеличить", 32
        )
        self.btn_zoom_fit = self._make_button(
            "FIT", "Вписать в экран (Ctrl+0)", 44
        )
        self.btn_find = self._make_button(
            "FIND", "Найти (Ctrl+F)", 52
        )

        layout.addWidget(self.btn_zoom_out)
        layout.addWidget(self.btn_zoom_in)
        layout.addWidget(self.btn_zoom_fit)
        layout.addWidget(self.btn_find)

    def _make_button(self, text, tooltip, width):
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        btn.setFixedHeight(26)
        btn.setFixedWidth(width)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def _apply_style(self):
        self.setStyleSheet(
            """
            QFrame#dialogueFloatingToolbar {
                background: #17191C;
                border: 1px solid #2A2D33;
                border-radius: 6px;
            }
            QFrame#dialogueFloatingToolbar QPushButton {
                background: transparent;
                color: #858B93;
                border: none;
                border-radius: 3px;
                font-size: 10px;
                font-weight: 700;
                padding: 0;
            }
            QFrame#dialogueFloatingToolbar QPushButton:hover {
                background: #202328;
                color: #E5E5E5;
            }
            QFrame#dialogueFloatingToolbar QPushButton:pressed {
                background: #292D32;
            }
            """
        )