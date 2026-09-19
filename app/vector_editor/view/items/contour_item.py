"""
ContourItem — QGraphicsObject, рисует замкнутый контур.

Путь строится из модели VectorContour.
Тонкая чёрная линия (cosmetic pen — не зависит от zoom).

Создаёт и держит NodeItem'ы для всех вершин.
При перемещении узла — перестраивает путь.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsObject

from ...model.contour import VectorContour
from .node_item import NodeItem


class ContourItem(QGraphicsObject):
    """Визуализация VectorContour."""

    LINE_WIDTH = 1.2
    LINE_COLOR = "#1A1A1A"

    def __init__(self, contour: VectorContour, parent=None):
        super().__init__(parent)

        self._contour = contour
        self._nodes: list[NodeItem] = []

        self.setZValue(1.0)

        self._rebuild_nodes()
        self._rebuild_path()

    # ------------------------------------------------------------

    @property
    def contour(self) -> VectorContour:
        return self._contour

    # ------------------------------------------------------------

    def boundingRect(self) -> QRectF:
        return self._path.boundingRect().adjusted(
            -1.0, -1.0, 1.0, 1.0
        )

    def paint(self, painter, option, widget=None) -> None:
        painter.setRenderHint(painter.RenderHint.Antialiasing, True)

        pen = QPen(QColor(self.LINE_COLOR), self.LINE_WIDTH)
        pen.setCosmetic(True)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)

        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.drawPath(self._path)

    # ------------------------------------------------------------

    def _rebuild_path(self) -> None:
        """Строит QPainterPath из точек модели."""
        self.prepareGeometryChange()

        path = QPainterPath()
        pts = self._contour.points
        if not pts:
            self._path = path
            return

        path.moveTo(pts[0][0], pts[0][1])
        for (x, y) in pts[1:]:
            path.lineTo(x, y)
        if self._contour.closed:
            path.closeSubpath()

        self._path = path
        self.update()

    def _rebuild_nodes(self) -> None:
        """Создаёт NodeItem'ы для всех вершин (удаляет старые)."""
        for node in self._nodes:
            if node.scene():
                node.scene().removeItem(node)
            node.setParentItem(None)
        self._nodes.clear()

        for idx, (x, y) in enumerate(self._contour.points):
            node = NodeItem(idx, x, y)
            node.setParentItem(self)
            node.node_moved.connect(self._on_node_moved)
            self._nodes.append(node)

    # ------------------------------------------------------------

    def _on_node_moved(self, idx: int, x: float, y: float) -> None:
        """Узел сдвинулся — обновляем модель и перестраиваем путь."""
        self._contour.set_point(idx, x, y)
        self._rebuild_path()
