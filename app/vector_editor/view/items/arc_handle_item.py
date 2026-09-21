"""
ArcHandleItem — кружок-ручка на середине изогнутой дуги.
Тянешь его мышью → дуга гнётся.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject


class ArcHandleItem(QGraphicsObject):
    """Кружок для изменения кривизны одного ребра."""

    moved = Signal(int)   # индекс ребра (main)
    released = Signal(int)

    RADIUS_M = 0.40   # ~20 px при ppm=50

    def __init__(self, edge_index: int, x: float, y: float, parent=None):
        super().__init__(parent)
        self._edge_index = edge_index
        self._dragging = False
        self._start_offset = QPointF(0, 0)

        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False,
        )
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False,
        )
        self.setZValue(200.0)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setAcceptHoverEvents(True)
        # Кружок рисуется всегда 8 px, независимо от зума сцены
        # Работает в сцене (метры), не пикселях — иначе hit-test ломается

        self.setPos(x, y)

    def edge_index(self) -> int:
        return self._edge_index

    def set_center(self, x: float, y: float) -> None:
        self.prepareGeometryChange()
        self.setPos(x, y)

    def boundingRect(self) -> QRectF:
        r = self.RADIUS_M
        pad = r + 0.05
        return QRectF(-pad, -pad, 2 * pad, 2 * pad)

    def paint(self, painter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        r = self.RADIUS_M

        if self._dragging:
            pen_color = QColor("#FF6B00")
            fill_color = QColor("#FFE0B2")
        else:
            pen_color = QColor("#0055CC")
            fill_color = QColor("#FFFFFF")

        pen = QPen(pen_color, 0.03)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(QBrush(fill_color))
        painter.drawEllipse(QPointF(0, 0), r, r)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(pen_color))
        inner = r * 0.35
        painter.drawEllipse(QPointF(0, 0), inner, inner)

    def hoverEnterEvent(self, event) -> None:
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            scene_pos = event.scenePos()
            self._start_offset = scene_pos - self.scenePos()
            event.accept()
            self.update()
            return
        event.ignore()

    def mouseMoveEvent(self, event) -> None:
        if not self._dragging:
            event.ignore()
            return
        new_scene_pos = event.scenePos() - self._start_offset
        parent = self.parentItem()
        if parent is not None:
            local = parent.mapFromScene(new_scene_pos)
            self.setPos(local)
        else:
            self.setPos(new_scene_pos)
        self.moved.emit(self._edge_index)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if self._dragging:
            self._dragging = False
            event.accept()
            self.update()
            self.released.emit(self._edge_index)
            return
        event.ignore()