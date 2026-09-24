"""
MountPointItem - визуальный маркер точки крепления в VE.

НЕ путать с ExtraNodeItem (это геометрическая точка).
MountPointItem - визуализация семантической MountPoint.

Item - top-level item сцены, чтобы hit-test работал корректно.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPen, QFont, QPainterPath
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject


NODE_RADIUS = 12.0
FONT_SIZE = 10


GHOST_RADIUS = 6.0
GHOST_MAX_DRAW = 50
GHOST_COLOR = QColor("#FFD93D")
GHOST_OPACITY = 0.4
BOUNDING_PAD = 1000.0


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
        count_x: int = 1,
        count_y: int = 1,
        spacing_x: float = 0.0,
        spacing_y: float = 0.0,
        parent=None,
    ):
        super().__init__(parent)

        self._mp_id = mp_id
        self._role = role or ""

        # V22: distribution — для ghost-точек при выделении
        self._count_x = max(1, int(count_x))
        self._count_y = max(1, int(count_y))
        self._spacing_x = max(0.0, float(spacing_x))
        self._spacing_y = max(0.0, float(spacing_y))

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
        # V22: с запасом — чтобы влезали ghost-точки при выделении
        p = BOUNDING_PAD
        return QRectF(-p, -p, 2 * p, 2 * p)

    def shape(self):
        # V22: кликабельна ТОЛЬКО базовая точка, не ghost'ы
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

    def _draw_ghosts(self, painter) -> None:
        """Ghost-точки при выделении: показывают распределение.

        ItemIgnoresTransformations=True — рисуем прямо в пикселях,
        transform уже учтён. spacing в метрах * ppm = пиксели.
        """
        if self._count_x == 1 and self._count_y == 1:
            return

        # ppm — пиксели на метр (масштаб Canvas)
        ppm = 50.0
        if self.scene() and self.scene().views():
            try:
                ppm = abs(
                    self.scene().views()[0].transform().m11()
                ) or 50.0
            except Exception:
                ppm = 50.0

        ghost_pen = QPen(QColor("#1A1A1A"), 1.0)
        ghost_pen.setCosmetic(True)
        painter.setPen(ghost_pen)
        painter.setBrush(QBrush(GHOST_COLOR))

        painter.save()
        painter.setOpacity(GHOST_OPACITY)

        drawn = 0
        for iy in range(self._count_y):
            for ix in range(self._count_x):
                if ix == 0 and iy == 0:
                    continue
                if drawn >= GHOST_MAX_DRAW:
                    painter.restore()
                    return

                # пиксели относительно item
                gx = ix * self._spacing_x * ppm
                gy = -iy * self._spacing_y * ppm

                painter.drawEllipse(
                    QPointF(gx, gy), GHOST_RADIUS, GHOST_RADIUS,
                )
                drawn += 1

        painter.restore()

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(
            painter.RenderHint.Antialiasing, True,
        )

        # V22: ghost'ы при выделении — под базовым маркером
        if self.isSelected():
            self._draw_ghosts(painter)

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
