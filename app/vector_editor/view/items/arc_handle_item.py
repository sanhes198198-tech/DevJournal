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

    moved = Signal(int)
    released = Signal(int)

    # Радиус в ПИКСЕЛЯХ на экране — пересчитывается в метры динамически
    RADIUS_PX = 8.0
    # Ограничения в метрах (защита от экстрим-зума)
    MIN_RADIUS_M = 0.03
    MAX_RADIUS_M = 0.60

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

        self.setPos(x, y)

    def edge_index(self) -> int:
        return self._edge_index

    def set_center(self, x: float, y: float) -> None:
        self.prepareGeometryChange()
        self.setPos(x, y)

    def radius_m(self) -> float:
        """Текущий радиус в метрах — 8 px на экране."""
        scene = self.scene()
        if scene is None:
            return 0.16
        views = scene.views()
        if not views:
            return 0.16
        ppm = abs(views[0].transform().m11()) or 50.0
        r = self.RADIUS_PX / ppm
        if r < self.MIN_RADIUS_M:
            return self.MIN_RADIUS_M
        if r > self.MAX_RADIUS_M:
            return self.MAX_RADIUS_M
        return r

    # Радиус для клика (в пикселях) — чуть больше визуального
    CLICK_RADIUS_PX = 14.0

    def click_radius_m(self) -> float:
        """Радиус для hit-test — 14 px на экране."""
        scene = self.scene()
        if scene is None:
            return 0.28
        views = scene.views()
        if not views:
            return 0.28
        ppm = abs(views[0].transform().m11()) or 50.0
        r = self.CLICK_RADIUS_PX / ppm
        if r < 0.05:
            return 0.05
        if r > self.MAX_RADIUS_M:
            return self.MAX_RADIUS_M
        return r

    def boundingRect(self) -> QRectF:
        # Покрывает максимально возможный радиус + запас
        r = self.MAX_RADIUS_M + 0.05
        return QRectF(-r, -r, 2 * r, 2 * r)

    def shape(self) -> "QPainterPath":
        """Точная зона клика — маленький круг, не весь bbox.

        Без этого Qt считает клик «по хендлу» в радиусе 0.6 м —
        даже если визуально далеко от кружка.
        """
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        r = self.click_radius_m()
        path.addEllipse(QPointF(0, 0), r, r)
        return path

    def paint(self, painter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        r = self.radius_m()
        ppm = r and (self.RADIUS_PX / r) or 50.0

        if self._dragging:
            pen_color = QColor("#FF6B00")
            fill_color = QColor("#FFE0B2")
        else:
            pen_color = QColor("#0055CC")
            fill_color = QColor("#FFFFFF")

        pen = QPen(pen_color, 2.0 / ppm)
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