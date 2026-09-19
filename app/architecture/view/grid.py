"""
GridLayer — многоуровневая сетка для архитектурного canvas.

Рисуется в drawBackground сцены. Всё в метрах.

Сетка знает только про:
  - метры (координаты линии)
  - пикселей_на_метр (ppm)
  - видимую область (rect_meters)

Не знает про сцену, view, документ. Тестируется отдельно.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QLineF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen


class GridLayer:
    """Многоуровневая сетка."""

    # Шаги в метрах
    STEP_FINE = 0.1
    STEP_MID = 0.5
    STEP_COARSE = 1.0
    STEP_MACRO = 5.0

    # Порог ppm (пикселей на метр), выше которого уровень виден
    PPM_SHOW_FINE = 200.0
    PPM_SHOW_MID = 50.0
    PPM_SHOW_COARSE = 20.0
    # MACRO всегда видно

    # Цвета
    COLOR_FINE = QColor("#1F1F1F")
    COLOR_MID = QColor("#2A2A2A")
    COLOR_COARSE = QColor("#353535")
    COLOR_MACRO = QColor("#4A4A4A")
    COLOR_AXIS_X = QColor("#7A3A3A")   # горизонтальная ось (Y=0)
    COLOR_AXIS_Y = QColor("#3A7A3A")   # вертикальная ось (X=0)

    def draw(
        self,
        painter: QPainter,
        rect_meters: QRectF,
        ppm: float,
    ) -> None:
        """Рисует сетку в указанной области.

        rect_meters — видимая область в метрах (scene coords).
        ppm — пикселей на метр (для решения, какие уровни показывать).
        """
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # 1. Уровни — от крупного к мелкому (крупный под мелким)
        if ppm >= self.PPM_SHOW_COARSE:
            self._draw_level(painter, rect_meters, self.STEP_COARSE, self.COLOR_COARSE, 1.0)
        if ppm >= self.PPM_SHOW_MID:
            self._draw_level(painter, rect_meters, self.STEP_MID, self.COLOR_MID, 1.0)
        if ppm >= self.PPM_SHOW_FINE:
            self._draw_level(painter, rect_meters, self.STEP_FINE, self.COLOR_FINE, 1.0)
        # MACRO — всегда
        self._draw_level(painter, rect_meters, self.STEP_MACRO, self.COLOR_MACRO, 1.0)

        # 2. Оси поверх сетки
        self._draw_axes(painter, rect_meters)

        painter.restore()

    # ------------------------------------------------------------

    def _draw_level(
        self,
        painter: QPainter,
        rect: QRectF,
        step: float,
        color: QColor,
        width: float,
    ) -> None:
        """Рисует один уровень сетки."""
        pen = QPen(color, width)
        pen.setCosmetic(True)
        painter.setPen(pen)

        # Вертикальные линии (по X)
        x0 = math.floor(rect.left() / step) * step
        x = x0
        while x <= rect.right():
            painter.drawLine(QLineF(x, rect.top(), x, rect.bottom()))
            x += step

        # Горизонтальные линии (по Y)
        y0 = math.floor(rect.top() / step) * step
        y = y0
        while y <= rect.bottom():
            painter.drawLine(QLineF(rect.left(), y, rect.right(), y))
            y += step

    def _draw_axes(self, painter: QPainter, rect: QRectF) -> None:
        """Оси X=0 и Y=0."""
        pen_x = QPen(self.COLOR_AXIS_X, 1.5)
        pen_x.setCosmetic(True)

        pen_y = QPen(self.COLOR_AXIS_Y, 1.5)
        pen_y.setCosmetic(True)

        # Горизонтальная ось (Y=0)
        if rect.top() <= 0.0 <= rect.bottom():
            painter.setPen(pen_x)
            painter.drawLine(QLineF(rect.left(), 0.0, rect.right(), 0.0))

        # Вертикальная ось (X=0)
        if rect.left() <= 0.0 <= rect.right():
            painter.setPen(pen_y)
            painter.drawLine(QLineF(0.0, rect.top(), 0.0, rect.bottom()))
