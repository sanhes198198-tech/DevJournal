"""
GridLayer — сетка для сцены Constructor (1×1 м).
"""
from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPen


class GridLayer:
    MAJOR_EVERY = 10   # каждая 10-я линия — толще
    MINOR_COLOR = QColor("#E5E5E5")
    MAJOR_COLOR = QColor("#B0B0B0")
    MINOR_WIDTH = 1.0
    MAJOR_WIDTH = 1.6

    def draw(self, painter, rect: QRectF, ppm: float) -> None:
        if ppm < 3.0:
            return

        left = int(rect.left()) - 1
        right = int(rect.right()) + 1
        top = int(rect.top()) - 1
        bottom = int(rect.bottom()) + 1

        # Пропускаем слишком частые линии
        step = 1
        if ppm < 8:
            step = 5
        elif ppm < 20:
            step = 2

        minor_pen = QPen(self.MINOR_COLOR, self.MINOR_WIDTH)
        minor_pen.setCosmetic(True)
        major_pen = QPen(self.MAJOR_COLOR, self.MAJOR_WIDTH)
        major_pen.setCosmetic(True)

        # Вертикальные
        for x in range(left, right + 1, step):
            pen = (
                major_pen
                if x % self.MAJOR_EVERY == 0
                else minor_pen
            )
            painter.setPen(pen)
            painter.drawLine(x, top, x, bottom)

        # Горизонтальные
        for y in range(top, bottom + 1, step):
            pen = (
                major_pen
                if y % self.MAJOR_EVERY == 0
                else minor_pen
            )
            painter.setPen(pen)
            painter.drawLine(left, y, right, y)
