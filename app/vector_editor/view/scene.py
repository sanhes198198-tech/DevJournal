"""
VectorScene — QGraphicsScene с белым фоном.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QGraphicsScene


SCENE_HALF = 1000.0
SCENE_RECT = QRectF(-SCENE_HALF, -SCENE_HALF, SCENE_HALF * 2, SCENE_HALF * 2)


class VectorScene(QGraphicsScene):
    """Сцена: белый фон, координаты в метрах."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setSceneRect(SCENE_RECT)
        self.setBackgroundBrush(QBrush(QColor("#FFFFFF")))
