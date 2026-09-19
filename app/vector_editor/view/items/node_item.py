"""
NodeItem — маркер одной вершины контура.

Хранит node_id (стабильный идентификатор для semantic_groups).
Умеет подсвечиваться (highlight) — когда выбрана группа.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject


NODE_PIXELS = 10.0

HIGHLIGHT_BORDER = QColor("#FF6B00")   # оранжевый


class NodeItem(QGraphicsObject):
    """Маркер одной вершины контура."""

    node_moved = Signal(int, float, float)
    drag_started = Signal()
    drag_finished = Signal()

    def __init__(
        self,
        idx: int,
        x: float,
        y: float,
        node_id: str = "",
        parent=None,
    ):
        super().__init__(parent)

        self._idx = idx
        self._node_id = node_id

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
        self._highlight = False
        self.setAcceptHoverEvents(True)

    # ------------------------------------------------------------

    @property
    def idx(self) -> int:
        return self._idx

    @property
    def node_id(self) -> str:
        return self._node_id

    def set_highlight(self, value: bool) -> None:
        if self._highlight != value:
            self._highlight = value
            self.update()

    def is_highlighted(self) -> bool:
        return self._highlight

    # ------------------------------------------------------------

    def _half_size_m(self, painter) -> float:
        ppm = abs(painter.transform().m11()) or 50.0
        return (NODE_PIXELS / 2.0) / ppm

    def boundingRect(self) -> QRectF:
        pad = 0.5
        return QRectF(-pad, -pad, pad * 2, pad * 2)

    def paint(self, painter, option, widget=None) -> None:
        half = self._half_size_m(painter)

        # Приоритет отображения:
        # 1) selected (синяя заливка)
        # 2) highlight (оранжевая обводка, белая заливка)
        # 3) hover (светлая заливка)
        # 4) обычный (белая заливка)
        if self.isSelected():
            fill = QColor("#0055CC")
            border = QColor("#003399")
            pen_width = 0
        elif self._highlight:
            fill = QColor("#FFFFFF")
            border = HIGHLIGHT_BORDER
            pen_width = 2.5
        elif self._hover:
            fill = QColor("#8AB4FF")
            border = QColor("#0055CC")
            pen_width = 0
        else:
            fill = QColor("#FFFFFF")
            border = QColor("#0055CC")
            pen_width = 0

        painter.setBrush(QBrush(fill))
        pen = QPen(border, pen_width)
        pen.setCosmetic(True)
        painter.setPen(pen)

        painter.drawRect(QRectF(-half, -half, half * 2, half * 2))

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

    # ------------------------------------------------------------

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.node_moved.emit(self._idx, value.x(), value.y())
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update()
        return super().itemChange(change, value)
