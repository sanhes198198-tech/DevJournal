"""
VectorScene — QGraphicsScene с адаптивной сеткой.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QLineF, QRectF
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsScene


SCENE_HALF = 1000.0
SCENE_RECT = QRectF(-SCENE_HALF, -SCENE_HALF, SCENE_HALF * 2, SCENE_HALF * 2)


class VectorScene(QGraphicsScene):
    """Сцена: белый фон, координаты в метрах, адаптивная сетка."""

    # Минимальное расстояние между мелкими линиями (пиксели)
    MIN_PIXELS_MINOR = 8.0
    # Каждая N-я линия — крупная
    MAJOR_MULTIPLIER = 5

    # Возможные шаги сетки (метры)
    STEPS = [
        0.001, 0.002, 0.005,
        0.01, 0.02, 0.05,
        0.1, 0.2, 0.5,
        1.0, 2.0, 5.0,
        10.0, 20.0, 50.0,
        100.0, 200.0, 500.0,
    ]

    GRID_COLOR_MINOR = QColor("#EEEEEE")
    GRID_COLOR_MAJOR = QColor("#CCCCCC")

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setSceneRect(SCENE_RECT)
        self.grid_enabled = True
        self.snap_enabled = True
        self.snap_step = 0.1

    def _pick_step(self, ppm: float) -> float:
        """Выбрать шаг сетки так, чтобы мелкая линия была >= MIN_PIXELS."""
        for s in self.STEPS:
            if s * ppm >= self.MIN_PIXELS_MINOR:
                return s
        return self.STEPS[-1]

    def drawBackground(self, painter, rect):
        painter.fillRect(rect, QBrush(QColor("#FFFFFF")))

        if not self.grid_enabled:
            return

        views = self.views()
        if not views:
            return
        ppm = abs(views[0].transform().m11()) or 50.0

        minor_step = self._pick_step(ppm)
        major_step = minor_step * self.MAJOR_MULTIPLIER

        # Мелкая сетка
        pen_minor = QPen(self.GRID_COLOR_MINOR, 1)
        pen_minor.setCosmetic(True)
        painter.setPen(pen_minor)

        eps = minor_step * 0.001

        x = math.floor(rect.left() / minor_step) * minor_step
        while x <= rect.right():
            k = x / major_step
            if abs(k - round(k)) > 0.001:
                painter.drawLine(QLineF(x, rect.top(), x, rect.bottom()))
            x += minor_step

        y = math.floor(rect.top() / minor_step) * minor_step
        while y <= rect.bottom():
            k = y / major_step
            if abs(k - round(k)) > 0.001:
                painter.drawLine(QLineF(rect.left(), y, rect.right(), y))
            y += minor_step

        # Крупная сетка
        pen_major = QPen(self.GRID_COLOR_MAJOR, 1)
        pen_major.setCosmetic(True)
        painter.setPen(pen_major)

        x = math.floor(rect.left() / major_step) * major_step
        while x <= rect.right():
            painter.drawLine(QLineF(x, rect.top(), x, rect.bottom()))
            x += major_step

        y = math.floor(rect.top() / major_step) * major_step
        while y <= rect.bottom():
            painter.drawLine(QLineF(rect.left(), y, rect.right(), y))
            y += major_step