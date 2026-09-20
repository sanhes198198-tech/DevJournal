"""
ExtraNodeItem — маркер extra-only узла контура.

Отличается от NodeItem:
  - идентифицируется по node_id (не по index — extra-узлы не имеют
    позиции в main-контуре);
  - визуально меньше — маленький кружок зелёного цвета;
  - координаты берутся из VectorContour.extra_points.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject


NODE_PIXELS = 10.0
HALF_PIXELS = 5.0


class ExtraNodeItem(QGraphicsObject):
    """Маркер extra-only узла."""

    node_moved = Signal(str, float, float)   # node_id, x, y
    drag_started = Signal()
    drag_finished = Signal()

    FILL = "#FFFFFF"
    BORDER = "#009944"
    HOVER_FILL = "#90EE90"

    def __init__(
        self,
        node_id: str,
        x: float,
        y: float,
        parent=None,
    ):
        super().__init__(parent)

        self._node_id = node_id

        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True,
        )
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True,
        )
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges,
            True,
        )
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations,
            True,
        )

        self.setZValue(11.0)
        self.setPos(QPointF(x, y))

        self._hover = False
        self.setAcceptHoverEvents(True)

    # ------------------------------------------------------------

    @property
    def node_id(self) -> str:
        return self._node_id

    # ------------------------------------------------------------

    def boundingRect(self) -> QRectF:
        return QRectF(
            -HALF_PIXELS, -HALF_PIXELS,
            NODE_PIXELS, NODE_PIXELS,
        )

    def shape(self):
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path

    def paint(self, painter, option, widget=None) -> None:
        if self.isSelected():
            fill = QColor("#0055CC")
            border = QColor("#003399")
            pen_width = 0
        elif self._hover:
            fill = QColor(self.HOVER_FILL)
            border = QColor(self.BORDER)
            pen_width = 0
        else:
            fill = QColor(self.FILL)
            border = QColor(self.BORDER)
            pen_width = 0

        painter.setBrush(QBrush(fill))
        pen = QPen(border, pen_width)
        pen.setCosmetic(True)
        painter.setPen(pen)

        painter.drawRect(
            QRectF(
                -HALF_PIXELS, -HALF_PIXELS,
                NODE_PIXELS, NODE_PIXELS,
            )
        )

    # ------------------------------------------------------------

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.drag_started.emit()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.drag_finished.emit()

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

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.node_moved.emit(
                self._node_id, value.x(), value.y(),
            )
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update()
        return super().itemChange(change, value)
