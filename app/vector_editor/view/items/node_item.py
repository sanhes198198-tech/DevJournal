"""
NodeItem — маркер одной вершины контура.

Размер в пикселях экрана (косметический) — вычисляется в paint().
Выделяется как QGraphicsItem.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject


NODE_PIXELS = 10.0


class NodeItem(QGraphicsObject):
    """Маркер одной вершины контура."""

    node_moved = Signal(int, float, float)

    def __init__(self, idx: int, x: float, y: float, parent=None):
        super().__init__(parent)

        self._idx = idx

        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
            True,
        )
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
            True,
        )
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges,
            True,
        )

        self.setZValue(10.0)
        self.setPos(QPointF(x, y))

        self._hover = False
        self.setAcceptHoverEvents(True)

    # ------------------------------------------------------------

    @property
    def idx(self) -> int:
        return self._idx

    def _half_size_m(self, painter) -> float:
        ppm = abs(painter.transform().m11()) or 50.0
        return (NODE_PIXELS / 2.0) / ppm

    def boundingRect(self) -> QRectF:
        pad = 0.5
        return QRectF(-pad, -pad, pad * 2, pad * 2)

    def paint(self, painter, option, widget=None) -> None:
        half = self._half_size_m(painter)

        if self.isSelected():
            fill = QColor("#0055CC")
            border = QColor("#003399")
        elif self._hover:
            fill = QColor("#8AB4FF")
            border = QColor("#0055CC")
        else:
            fill = QColor("#FFFFFF")
            border = QColor("#0055CC")

        painter.setBrush(QBrush(fill))
        pen = QPen(border, 0)
        pen.setCosmetic(True)
        painter.setPen(pen)

        painter.drawRect(QRectF(-half, -half, half * 2, half * 2))

    # ------------------------------------------------------------

    def hoverEnterEvent(self, event):
        self._hover = True
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hover = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
        super().hoverLeaveEvent(event)

    # ------------------------------------------------------------

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.node_moved.emit(self._idx, value.x(), value.y())
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update()
        return super().itemChange(change, value)
