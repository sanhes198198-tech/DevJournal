"""
RulerWidget — линейка по краю сцены Constructor.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QWidget


NICE_STEPS = [0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0]


class RulerWidget(QWidget):
    THICKNESS = 22
    BG = QColor("#F0F2F5")
    LINE = QColor("#9AA0A6")
    TEXT = QColor("#5A5F68")
    SUB_LINE = QColor("#C8CDD2")

    def __init__(self, canvas, orientation="h", parent=None):
        super().__init__(parent)
        self._canvas = canvas
        self._orientation = orientation
        if orientation == "h":
            self.setFixedHeight(self.THICKNESS)
        else:
            self.setFixedWidth(self.THICKNESS)
        self.setStyleSheet("background: #F0F2F5;")

    def _pick_step(self, ppm):
        target_px = 60
        for s in NICE_STEPS:
            if s * ppm >= target_px:
                return s
        return NICE_STEPS[-1]

    @staticmethod
    def _format(v):
        if abs(v) < 1e-9:
            return "0"
        if abs(v) >= 10:
            return f"{int(round(v))}"
        if abs(v) >= 1:
            return f"{v:.1f}".rstrip("0").rstrip(".")
        return f"{v:.2f}".rstrip("0").rstrip(".")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.BG)

        ppm = self._canvas.current_ppm()
        if ppm <= 0:
            return

        step = self._pick_step(ppm)

        font = QFont("sans-serif")
        font.setPixelSize(10)
        painter.setFont(font)
        fm = QFontMetrics(font)

        if self._orientation == "h":
            self._paint_horizontal(painter, fm, step)
        else:
            self._paint_vertical(painter, fm, step)

    def _paint_horizontal(self, painter, fm, step):
        w = self.width()
        left_scene = self._canvas.mapToScene(0, 0).x()
        right_scene = self._canvas.mapToScene(w, 0).x()

        start = int(left_scene / step) * step
        while start > left_scene:
            start -= step

        x = start
        while x <= right_scene + step:
            px = self._canvas.mapFromScene(QPointF(x, 0)).x()
            if 0 <= px <= w:
                painter.setPen(QPen(self.LINE, 1))
                painter.drawLine(int(px), self.THICKNESS - 7, int(px), self.THICKNESS)
                text = self._format(x)
                painter.setPen(self.TEXT)
                painter.drawText(int(px) + 2, self.THICKNESS - 9, text)
            for i in range(1, 5):
                sx = x + step * i / 5
                spx = self._canvas.mapFromScene(QPointF(sx, 0)).x()
                if 0 <= spx <= w:
                    painter.setPen(QPen(self.SUB_LINE, 1))
                    painter.drawLine(int(spx), self.THICKNESS - 4, int(spx), self.THICKNESS)
            x += step

    def _paint_vertical(self, painter, fm, step):
        h = self.height()
        top_scene = self._canvas.mapToScene(0, 0).y()
        bottom_scene = self._canvas.mapToScene(0, h).y()

        start = int(top_scene / step) * step
        while start > top_scene:
            start -= step

        y = start
        while y <= bottom_scene + step:
            py = self._canvas.mapFromScene(QPointF(0, y)).y()
            if 0 <= py <= h:
                painter.setPen(QPen(self.LINE, 1))
                painter.drawLine(self.THICKNESS - 7, int(py), self.THICKNESS, int(py))
                text = self._format(y)
                painter.setPen(self.TEXT)
                painter.drawText(2, int(py) - 2, text)
            for i in range(1, 5):
                sy = y + step * i / 5
                spy = self._canvas.mapFromScene(QPointF(0, sy)).y()
                if 0 <= spy <= h:
                    painter.setPen(QPen(self.SUB_LINE, 1))
                    painter.drawLine(self.THICKNESS - 4, int(spy), self.THICKNESS, int(spy))
            y += step
