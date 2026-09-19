"""
ContourItem — QGraphicsObject, рисует замкнутый контур.

Путь строится из модели VectorContour.
Тонкая чёрная линия (cosmetic pen — не зависит от zoom).

Создаёт и держит NodeItem'ы для всех вершин.
При перемещении узла — перестраивает путь.

Поддерживает:
  - двойной клик по сегменту → вставка нового узла;
  - remove_node(idx) — удаление узла;
  - set_editable(bool) — показывать / скрывать узлы.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPainterPathStroker, QPen
from PySide6.QtWidgets import QGraphicsObject

from ...model.contour import VectorContour
from ...model.geometry import dist_point_to_segment
from .node_item import NodeItem


class ContourItem(QGraphicsObject):
    """Визуализация VectorContour."""

    LINE_WIDTH = 1.2
    LINE_COLOR = "#1A1A1A"
    LINE_COLOR_SELECTED = "#0055CC"

    HIT_THRESHOLD_PX = 8.0

    def __init__(self, contour: VectorContour, parent=None):
        super().__init__(parent)

        self._contour = contour
        self._nodes: list[NodeItem] = []
        self._editable: bool = True
        self._last_ppm: float = 50.0

        self._path = QPainterPath()

        self.setFlag(
            self.GraphicsItemFlag.ItemIsSelectable,
            True,
        )
        self.setZValue(1.0)

        self._rebuild_nodes()
        self._rebuild_path()

    # ------------------------------------------------------------

    @property
    def contour(self) -> VectorContour:
        return self._contour

    # ------------------------------------------------------------

    def set_editable(self, editable: bool) -> None:
        """Показывать / скрывать узлы."""
        self._editable = editable
        for node in self._nodes:
            node.setVisible(editable)

    # ------------------------------------------------------------

    def boundingRect(self) -> QRectF:
        if self._path.isEmpty():
            return QRectF()
        return self._path.boundingRect().adjusted(
            -1.0, -1.0, 1.0, 1.0
        )

    def shape(self) -> QPainterPath:
        """Утолщённый контур — чтобы ловить клики по линии."""
        if self._path.isEmpty():
            return QPainterPath()

        ppm = self._last_ppm or 50.0
        stroke_w_m = self.HIT_THRESHOLD_PX / ppm

        stroker = QPainterPathStroker()
        stroker.setWidth(max(stroke_w_m, 0.01))
        return stroker.createStroke(self._path)

    def paint(self, painter, option, widget=None) -> None:
        self._last_ppm = abs(painter.transform().m11()) or 50.0

        painter.setRenderHint(painter.RenderHint.Antialiasing, True)

        color = (
            self.LINE_COLOR_SELECTED
            if self.isSelected()
            else self.LINE_COLOR
        )

        pen = QPen(QColor(color), self.LINE_WIDTH)
        pen.setCosmetic(True)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)

        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.drawPath(self._path)

    # ------------------------------------------------------------

    def _rebuild_path(self) -> None:
        self.prepareGeometryChange()

        path = QPainterPath()
        pts = self._contour.points
        if not pts:
            self._path = path
            self.update()
            return

        path.moveTo(pts[0][0], pts[0][1])
        for (x, y) in pts[1:]:
            path.lineTo(x, y)
        if self._contour.closed:
            path.closeSubpath()

        self._path = path
        self.update()

    def _rebuild_nodes(self) -> None:
        for node in self._nodes:
            if node.scene() is not None:
                node.scene().removeItem(node)
            node.setParentItem(None)
        self._nodes.clear()

        for idx, (x, y) in enumerate(self._contour.points):
            node = NodeItem(idx, x, y)
            node.setParentItem(self)
            node.node_moved.connect(self._on_node_moved)
            node.setVisible(self._editable)
            self._nodes.append(node)

    # ------------------------------------------------------------

    def _on_node_moved(self, idx: int, x: float, y: float) -> None:
        self._contour.set_point(idx, x, y)
        self._rebuild_path()

    # ------------------------------------------------------------

    def remove_node(self, idx: int) -> None:
        """Удалить узел по индексу. Требует >= 3 узлов после."""
        pts = self._contour.points
        if idx < 0 or idx >= len(pts):
            return
        if len(pts) <= 3:
            return  # нельзя опустить ниже 3

        pts.pop(idx)
        self._rebuild_nodes()
        self._rebuild_path()

    def insert_node_after_segment(self, seg_idx: int, t: float) -> int:
        """Вставить узел в сегмент seg_idx на параметре t (0..1).

        Возвращает индекс нового узла.
        """
        pts = self._contour.points
        n = len(pts)
        if n < 2:
            return -1
        if seg_idx < 0 or seg_idx >= n:
            return -1

        p1 = pts[seg_idx]
        p2 = pts[(seg_idx + 1) % n]

        x = p1[0] + t * (p2[0] - p1[0])
        y = p1[1] + t * (p2[1] - p1[1])

        pts.insert(seg_idx + 1, (x, y))
        self._rebuild_nodes()
        self._rebuild_path()
        return seg_idx + 1

    # ------------------------------------------------------------

    def mouseDoubleClickEvent(self, event) -> None:
        """Двойной клик — вставить узел в ближайший сегмент."""
        if not self._editable:
            super().mouseDoubleClickEvent(event)
            return

        scene_pos = event.scenePos()

        best_dist = float("inf")
        best_seg = -1
        best_t = 0.0

        pts = self._contour.points
        n = len(pts)
        if n < 2:
            super().mouseDoubleClickEvent(event)
            return

        segments = range(n) if self._contour.closed else range(n - 1)

        for i in segments:
            p1 = pts[i]
            p2 = pts[(i + 1) % n]

            d, t = dist_point_to_segment(
                scene_pos.x(), scene_pos.y(),
                p1[0], p1[1], p2[0], p2[1],
            )
            if d < best_dist:
                best_dist = d
                best_seg = i
                best_t = t

        ppm = self._last_ppm or 50.0
        threshold_m = self.HIT_THRESHOLD_PX / ppm

        if best_seg >= 0 and best_dist <= threshold_m:
            self.insert_node_after_segment(best_seg, best_t)
            event.accept()
            return

        super().mouseDoubleClickEvent(event)
