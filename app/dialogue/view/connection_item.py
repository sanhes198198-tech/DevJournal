"""
Визуальная связь между двумя портами узлов.

QGraphicsPathItem, который рисует кривую Безье между
source-портом и target-портом.

Связь живёт в координатах сцены (setPos(0,0)), а её path
пересчитывается при движении любого из узлов.
"""

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QColor,
    QPen,
    QPainter,
    QPainterPath,
)
from PySide6.QtWidgets import QGraphicsPathItem

from . import theme


# =========================================================
# СТИЛЬ
# =========================================================

LINE_WIDTH = 1.5
LINE_WIDTH_SELECTED = 2.0

COLOR_NORMAL = QColor(theme.CONN_NORMAL)
COLOR_SELECTED = QColor(theme.CONN_SELECT)

# Отступ для контрольных точек кривой Безье
CURVE_OFFSET = 60.0


# =========================================================
# СВЯЗЬ
# =========================================================

class DialogueConnectionItem(QGraphicsPathItem):
    """Визуальная кривая между двумя портами."""

    def __init__(
        self,
        model_connection,
        source_port_item,
        target_port_item,
        parent=None,
    ):
        super().__init__(parent)

        self.model_connection = model_connection
        self.connection_id = model_connection.id

        self.source_port_item = source_port_item
        self.target_port_item = target_port_item

        # Связь живёт в scene-координатах
        self.setPos(0.0, 0.0)

        # Не двигается — только выделяется
        self.setFlag(
            QGraphicsPathItem.GraphicsItemFlag.ItemIsMovable,
            False,
        )
        self.setFlag(
            QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable,
            True,
        )

        # Z ниже узлов, но выше фона
        self.setZValue(-1.0)

        # Сразу строим path
        self.update_path()

    # =========================================================
    # ГЕОМЕТРИЯ
    # =========================================================

    def update_path(self):
        """Пересчитывает кривую по текущим позициям портов."""
        if self.source_port_item is None or self.target_port_item is None:
            return

        src = self.source_port_item.scene_center()
        tgt = self.target_port_item.scene_center()

        path = self._build_path(src, tgt)
        self.setPath(path)

    def _build_path(self, src, tgt):
        """Строит QPainterPath между двумя точками."""
        path = QPainterPath()
        path.moveTo(src)

        dx = tgt.x() - src.x()

        # Горизонтальный отступ для контрольных точек
        offset = max(abs(dx) * 0.5, CURVE_OFFSET)

        cp1 = QPointF(src.x() + offset, src.y())
        cp2 = QPointF(tgt.x() - offset, tgt.y())

        path.cubicTo(cp1, cp2, tgt)

        return path

    def boundingRect(self):
        """Расширяем boundingRect, чтобы выделение работало."""
        r = super().boundingRect()
        return r.adjusted(-4.0, -4.0, 4.0, 4.0)

    # =========================================================
    # ОТРИСОВКА
    # =========================================================

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        if self.isSelected():
            color = COLOR_SELECTED
            width = LINE_WIDTH_SELECTED
        else:
            color = COLOR_NORMAL
            width = LINE_WIDTH

        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.drawPath(self.path())

    # =========================================================
    # УТИЛИТЫ
    # =========================================================

    def detach_from_ports(self):
        """
        Отвязывает связь от портов.

        Используется при удалении.
        """
        self.source_port_item = None
        self.target_port_item = None

    def __repr__(self):
        src = self.model_connection.source_node_id
        src_port = self.model_connection.source_port
        tgt = self.model_connection.target_node_id
        return (
            f"<DialogueConnectionItem id={self.connection_id!r} "
            f"{src}:{src_port} -> {tgt}>"
        )
