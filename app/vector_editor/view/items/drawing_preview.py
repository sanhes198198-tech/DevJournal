"""
DrawingPreviewItem — превью контура во время его создания.

Показывает:
  - синюю полилинию между уже поставленными точками
  - синюю пунктирную «резинку» от последней точки до курсора
  - синие точки в поставленных вершинах
  - первую точку крупнее и зеленее — цель для замыкания
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsObject


LINE_COLOR = "#0055CC"
FIRST_POINT_COLOR = "#00AA55"
POINT_RADIUS_PX = 4.0
FIRST_POINT_RADIUS_PX = 6.0
CLOSE_HINT_PX = 10.0  # радиус «подсветки» первой точки для замыкания


class DrawingPreviewItem(QGraphicsObject):
    """Препросмотр контура во время рисования."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._points: list[tuple[float, float]] = []
        self._cursor: tuple[float, float] | None = None

        self.setZValue(100.0)

    # ------------------------------------------------------------

    def add_point(self, x: float, y: float) -> None:
        self.prepareGeometryChange()
        self._points.append((float(x), float(y)))
        self.update()

    def set_cursor(self, x: float, y: float) -> None:
        self.prepareGeometryChange()
        self._cursor = (float(x), float(y))
        self.update()

    def clear_cursor(self) -> None:
        self.prepareGeometryChange()
        self._cursor = None
        self.update()

    def count(self) -> int:
        return len(self._points)

    def first_point(self) -> tuple[float, float] | None:
        if not self._points:
            return None
        return self._points[0]

    # ------------------------------------------------------------

    def boundingRect(self) -> QRectF:
        if not self._points and self._cursor is None:
            return QRectF()

        xs = [p[0] for p in self._points]
        ys = [p[1] for p in self._points]
        if self._cursor is not None:
            xs.append(self._cursor[0])
            ys.append(self._cursor[1])

        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)

        pad = 0.5
        return QRectF(
            x0 - pad, y0 - pad,
            (x1 - x0) + 2 * pad,
            (y1 - y0) + 2 * pad,
        )

    def paint(self, painter, option, widget=None) -> None:
        painter.setRenderHint(painter.RenderHint.Antialiasing, True)

        ppm = abs(painter.transform().m11()) or 50.0

        # --- Полилиния между поставленными точками ---
        if len(self._points) >= 2:
            pen = QPen(QColor(LINE_COLOR), 1.2)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            path = QPainterPath()
            path.moveTo(*self._points[0])
            for pt in self._points[1:]:
                path.lineTo(*pt)
            painter.drawPath(path)

        # --- «Резинка» от последней точки до курсора ---
        if self._cursor is not None and self._points:
            pen = QPen(QColor(LINE_COLOR), 1.0)
            pen.setCosmetic(True)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            last = self._points[-1]
            painter.drawLine(
                QPointF(*last),
                QPointF(*self._cursor),
            )

        # --- Точки ---
        painter.setPen(Qt.PenStyle.NoPen)

        # Обычные точки
        if len(self._points) > 1:
            painter.setBrush(QBrush(QColor(LINE_COLOR)))
            dot_r_m = POINT_RADIUS_PX / ppm
            for pt in self._points[1:]:
                painter.drawEllipse(QPointF(*pt), dot_r_m, dot_r_m)

        # Первая точка — крупнее, зелёная
        if self._points:
            first = self._points[0]

            # Если курсор близко — подсветить как «цель замыкания»
            if self._cursor is not None and len(self._points) >= 3:
                dist_px = math.hypot(
                    self._cursor[0] - first[0],
                    self._cursor[1] - first[1],
                ) * ppm
                if dist_px < CLOSE_HINT_PX:
                    painter.setBrush(QBrush(QColor(FIRST_POINT_COLOR)))
                    r = FIRST_POINT_RADIUS_PX * 1.4 / ppm
                    painter.drawEllipse(QPointF(*first), r, r)
                else:
                    painter.setBrush(QBrush(QColor(FIRST_POINT_COLOR)))
                    r = FIRST_POINT_RADIUS_PX / ppm
                    painter.drawEllipse(QPointF(*first), r, r)
            else:
                painter.setBrush(QBrush(QColor(FIRST_POINT_COLOR)))
                r = FIRST_POINT_RADIUS_PX / ppm
                painter.drawEllipse(QPointF(*first), r, r)
