"""
MountPointItem - визуальный маркер точки крепления в VE.

НЕ путать с ExtraNodeItem (это геометрическая точка).
MountPointItem - визуализация семантической MountPoint.

Item - top-level item сцены, чтобы hit-test работал корректно.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPen, QFont
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject


NODE_RADIUS = 12.0
FONT_SIZE = 10


ROLE_COLORS = {
    "window":     QColor("#4A9EFF"),
    "door":       QColor("#FFA94D"),
    "foundation": QColor("#8BC34A"),
    "cornice":    QColor("#FFD93D"),
    "decor":      QColor("#C77DFF"),
}
DEFAULT_COLOR = QColor("#AAAAAA")


class MountPointItem(QGraphicsObject):
    """Цветной круг с буквой роли."""

    moved = Signal(str, float, float)
    selected = Signal(str)
    drag_started = Signal()
    drag_finished = Signal()

    def __init__(
        self,
        mp_id: str,
        role: str | None,
        x: float,
        y: float,
        parent=None,
    ):
        super().__init__(parent)

        self._mp_id = mp_id
        self._role = role or ""

        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True,
        )
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True,
        )
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True,
        )
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations,
            True,
        )

        self.setZValue(100.0)

        # V22: не эмитить moved при первичной установке позиции
        self._initializing = True
        self.setPos(QPointF(x, y))
        self._initializing = False

        self._hover = False
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    @property
    def mp_id(self) -> str:
        return self._mp_id

    @property
    def role(self) -> str:
        return self._role

    def set_role(self, role: str | None) -> None:
        self._role = role or ""
        self.update()

    def boundingRect(self) -> QRectF:
        r = NODE_RADIUS + 3
        return QRectF(-r, -r, 2 * r, 2 * r)

    def shape(self):
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.addEllipse(QPointF(0, 0), NODE_RADIUS, NODE_RADIUS)
        return path

    def _fill_color(self) -> QColor:
        if self.isSelected():
            return QColor("#FFD93D").darker(120)
        if self._hover:
            return ROLE_COLORS.get(
                self._role, DEFAULT_COLOR
            ).lighter(120)
        return ROLE_COLORS.get(self._role, DEFAULT_COLOR)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(
            painter.RenderHint.Antialiasing, True,
        )

        fill = self._fill_color()
        border = QColor("#1A1A1A")

        painter.setBrush(QBrush(fill))
        pen = QPen(border, 1.5)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.drawEllipse(
            QPointF(0, 0), NODE_RADIUS, NODE_RADIUS,
        )

        if self._role:
            letter = self._role[0].upper()
            painter.setPen(QPen(QColor("#1A1A1A")))
            font = QFont()
            font.setPixelSize(FONT_SIZE)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(
                QRectF(
                    -NODE_RADIUS, -NODE_RADIUS,
                    2 * NODE_RADIUS, 2 * NODE_RADIUS,
                ),
                Qt.AlignmentFlag.AlignCenter,
                letter,
            )

    def hoverEnterEvent(self, event):
        self._hover = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hover = False
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.selected.emit(self._mp_id)
        self.drag_started.emit()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.drag_finished.emit()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if not getattr(self, "_initializing", False):
                p = self.pos()
                self.moved.emit(self._mp_id, p.x(), p.y())
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update()
        return super().itemChange(change, value)
