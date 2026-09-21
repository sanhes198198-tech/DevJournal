"""
NodeItem — маркер одной вершины контура.

ItemIgnoresTransformations: узел всегда ~10x10 ПИКСЕЛЕЙ на экране,
независимо от zoom. boundingRect в пикселях (не в метрах) —
это даёт ТОЧНЫЙ захват клика (раньше был 1x1 метр, соседи
перехватывали).
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject


NODE_PIXELS = 10.0
HALF_PIXELS = NODE_PIXELS / 2.0     # 5.0
HIGHLIGHT_BORDER = QColor("#FF6B00")


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
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True,
        )
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True,
        )
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True,
        )
        # Ключ: игнорируем view transform (zoom). Узел всегда
        # одинакового размера на экране, hit-test в пикселях.
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations,
            True,
        )

        self.setZValue(10.0)
        self._dragging = False
        self._snap_enabled = True
        self._snap_step = 0.1
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
    # GEOMETRY — в ПИКСЕЛЯХ (благодаря ItemIgnoresTransformations)
    # ------------------------------------------------------------

    def boundingRect(self) -> QRectF:
        return QRectF(
            -HALF_PIXELS, -HALF_PIXELS,
            NODE_PIXELS, NODE_PIXELS,
        )

    def shape(self):
        """Точная область захвата — квадрат NODE_PIXELS x NODE_PIXELS."""
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path

    def paint(self, painter, option, widget=None) -> None:
        # Приоритет: selected > highlight > hover > обычный
        # Приоритет: highlight > selected > hover > обычный.
        # Кликнул по параметру — видно всю группу, даже если
        # часть узлов была выделена.
        if self._highlight:
            fill = QColor("#FFFFFF")
            border = HIGHLIGHT_BORDER
            pen_width = 2.5
        elif self.isSelected():
            fill = QColor("#0055CC")
            border = QColor("#003399")
            pen_width = 0
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

        painter.drawRect(
            QRectF(
                -HALF_PIXELS, -HALF_PIXELS,
                NODE_PIXELS, NODE_PIXELS,
            )
        )

    # ------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
        super().mousePressEvent(event)
        self.drag_started.emit()

    def mouseReleaseEvent(self, event):
        self._dragging = False
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
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            # Мягкий snap: прилипаем только если близко к линии сетки
            if self._dragging and self._snap_enabled:
                scene = self.scene()
                ppm = 50.0
                if scene is not None:
                    views = scene.views()
                    if views:
                        ppm = abs(views[0].transform().m11()) or 50.0
                # Порог: 3 пикселя экрана в метрах
                threshold_m = 3.0 / ppm
                step = self._snap_step

                x = value.x()
                y = value.y()
                nx = round(x / step) * step
                ny = round(y / step) * step
                if abs(nx - x) <= threshold_m:
                    x = nx
                if abs(ny - y) <= threshold_m:
                    y = ny
                return QPointF(x, y)
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.node_moved.emit(self._idx, value.x(), value.y())
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update()
        return super().itemChange(change, value)
