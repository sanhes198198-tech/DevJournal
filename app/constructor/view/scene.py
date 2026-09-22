"""
ConstructorScene — QGraphicsScene для сборки зданий (Y ↑).
"""
from __future__ import annotations
from PySide6.QtCore import QRectF, Qt
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

    def set_ground_line(
        self, y: float | None, visible: bool = True,
    ) -> None:
        """V13: опорная линия (ground line).

        y=None — линии нет.
        """
        self._ground_y = float(y) if y is not None else None
        self._ground_visible = bool(visible)
        self.update()

    def ground_line_y(self) -> float | None:
        return getattr(self, "_ground_y", None)

    def ground_line_visible(self) -> bool:
        return getattr(self, "_ground_visible", True)

    def drawForeground(self, painter, rect: QRectF) -> None:
        super().drawForeground(painter, rect)

        # V13: опорная линия — длинный пунктир на всю ширину сцены.
        gy = getattr(self, "_ground_y", None)
        gv = getattr(self, "_ground_visible", True)
        if gy is not None and gv:
            from PySide6.QtGui import QPen, QColor
            from PySide6.QtCore import QPointF
            from PySide6.QtCore import Qt as _Qt
            pen = QPen(QColor("#0077CC"), 1.6)
            pen.setCosmetic(True)
            pen.setStyle(_Qt.PenStyle.DashLine)
            painter.setPen(pen)
            x0 = rect.left() if rect else SCENE_RECT.left()
            x1 = rect.right() if rect else SCENE_RECT.right()
            painter.drawLine(QPointF(x0, gy), QPointF(x1, gy))

        # Красный крест в (0,0) — точка отсчёта
        from PySide6.QtGui import QPen, QColor
        from PySide6.QtCore import QPointF

        # Размер крестика фиксированный в пикселях
        views = self.views()
        ppm = 50.0
        if views:
            ppm = abs(views[0].transform().m11()) or 50.0
        size_m = 8.0 / ppm   # 8 пикселей

        pen = QPen(QColor("#DD2222"), 1.4)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.drawLine(
            QPointF(-size_m, 0), QPointF(size_m, 0)
        )
        painter.drawLine(
            QPointF(0, -size_m), QPointF(0, size_m)
        )
