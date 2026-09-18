"""
Визуальная точка порта на узле диалога.

Порт — это маленький кружок на краю узла.
Input-порты — слева, output-порты — справа.

Порт не хранит данные модели. Он знает только:
- к какому узлу принадлежит (node_id)
- как называется (port_name: "input", "output", "opt_<uuid>")
- это вход или выход (is_input)
"""

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QPen, QBrush, QPainter
from PySide6.QtWidgets import QGraphicsItem


class PortItem(QGraphicsItem):
    """Визуальная точка порта на краю узла."""

    RADIUS = 5.0
    HOVER_RADIUS = 7.0

    COLOR_NORMAL = QColor("#9E9E9E")
    COLOR_HOVER = QColor("#4F7CFF")
    COLOR_BORDER = QColor("#666666")

    def __init__(
        self,
        node_id,
        port_name,
        is_input,
        parent=None,
    ):
        super().__init__(parent)

        self.node_id = node_id
        self.port_name = port_name
        self.is_input = bool(is_input)

        self._hovered = False

        self.setAcceptHoverEvents(True)
        self.setZValue(10)   # порты поверх узла

        # Не двигается сам — позиция задаётся родителем
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
            False,
        )
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
            False,
        )

    # =========================================================
    # ГЕОМЕТРИЯ
    # =========================================================

    def boundingRect(self):
        r = self.HOVER_RADIUS + 2.0
        return QRectF(-r, -r, 2 * r, 2 * r)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        radius = self.HOVER_RADIUS if self._hovered else self.RADIUS

        fill = self.COLOR_HOVER if self._hovered else self.COLOR_NORMAL

        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(self.COLOR_BORDER, 1.0))

        painter.drawEllipse(
            QPointF(0, 0),
            radius,
            radius,
        )

    # =========================================================
    # HOVER
    # =========================================================

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    # =========================================================
    # УТИЛИТЫ
    # =========================================================

    def scene_center(self):
        """Возвращает центр порта в координатах сцены."""
        return self.mapToScene(QPointF(0, 0))

    def __repr__(self):
        kind = "IN" if self.is_input else "OUT"
        return f"<PortItem {kind} {self.port_name!r} node={self.node_id!r}>"
