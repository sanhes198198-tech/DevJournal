"""
ConstructorScene — QGraphicsScene для сборки зданий (Y ↑).
"""
from __future__ import annotations
from PySide6.QtCore import QRectF
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QGraphicsScene

from .grid import GridLayer

SCENE_HALF = 500.0
SCENE_RECT = QRectF(-SCENE_HALF, -SCENE_HALF, SCENE_HALF * 2, SCENE_HALF * 2)


class ConstructorScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(SCENE_RECT)
        self.setBackgroundBrush(QBrush(QColor("#FFFFFF")))
        self._grid = GridLayer()

    def drawBackground(self, painter, rect: QRectF) -> None:
        super().drawBackground(painter, rect)

        ppm = 50.0
        views = self.views()
        if views:
            ppm = abs(views[0].transform().m11())

        self._grid.draw(painter, rect, ppm)
