"""
ContourItem — QGraphicsObject, рисует замкнутый контур.

Поддерживает:
  - узлы (NodeItem) — drag, del;
  - грани (edges) — hover / selection / extrude;
  - двойной клик по сегменту → вставка узла.

Внутреннее состояние:
  - _selected_edge_idx: int | None — выделенная грань;
  - _hover_edge_idx: int | None — грань под курсором.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainterPath, QPainterPathStroker, QPen
from PySide6.QtWidgets import QGraphicsObject

from ...model.contour import VectorContour
from ...model.geometry import dist_point_to_segment
from ...model.operations import extrude_face
from .node_item import NodeItem


class ContourItem(QGraphicsObject):
    """Визуализация VectorContour."""

    # Эмитится при любом изменении геометрии:
    # move узла, insert, remove.
    changed = Signal()

    LINE_WIDTH = 1.2
    LINE_WIDTH_SELECTED = 2.5
    LINE_WIDTH_HOVER = 2.0

    LINE_COLOR = "#1A1A1A"
    LINE_COLOR_SELECTED = "#0055CC"
    LINE_COLOR_HOVER = "#5588DD"

    HIT_THRESHOLD_PX = 8.0

    def __init__(self, contour: VectorContour, parent=None):
        super().__init__(parent)

        self._contour = contour
        self._nodes: list[NodeItem] = []
        self._editable: bool = True
        self._last_ppm: float = 50.0

        self._selected_edge_idx: int | None = None
        self._hover_edge_idx: int | None = None

        self._path = QPainterPath()

        self.setFlag(
            self.GraphicsItemFlag.ItemIsSelectable,
            True,
        )
        self.setAcceptHoverEvents(True)
        self.setZValue(1.0)

        self._rebuild_nodes()
        self._rebuild_path()

    # ============================================================
    # PUBLIC
    # ============================================================

    @property
    def contour(self) -> VectorContour:
        return self._contour

    @property
    def selected_edge_idx(self) -> int | None:
        return self._selected_edge_idx

    def clear_edge_selection(self) -> None:
        if self._selected_edge_idx is not None:
            self._selected_edge_idx = None
            self.update()

    def set_editable(self, editable: bool) -> None:
        self._editable = editable
        for node in self._nodes:
            node.setVisible(editable)

    # ============================================================
    # EXTRUDE
    # ============================================================

    def has_selected_edge(self) -> bool:
        return self._selected_edge_idx is not None

    def extrude_selected_face(self, distance: float) -> bool:
        """Вытянуть выделенную грань. Возвращает True при успехе."""
        if self._selected_edge_idx is None:
            return False

        new_points = extrude_face(
            self._contour.points,
            self._selected_edge_idx,
            distance,
        )
        if new_points is None:
            return False

        self._contour.points = new_points
        self._selected_edge_idx = None
        self._hover_edge_idx = None

        self._rebuild_nodes()
        self._rebuild_path()
        self.changed.emit()
        return True

    # ============================================================
    # ГЕОМЕТРИЯ
    # ============================================================

    def boundingRect(self) -> QRectF:
        if self._path.isEmpty():
            return QRectF()
        return self._path.boundingRect().adjusted(
            -1.0, -1.0, 1.0, 1.0
        )

    def shape(self) -> QPainterPath:
        if self._path.isEmpty():
            return QPainterPath()

        ppm = self._last_ppm or 50.0
        stroke_w_m = self.HIT_THRESHOLD_PX / ppm

        stroker = QPainterPathStroker()
        stroker.setWidth(max(stroke_w_m, 0.01))
        return stroker.createStroke(self._path)

    # ============================================================
    # PAINT
    # ============================================================

    def paint(self, painter, option, widget=None) -> None:
        self._last_ppm = abs(painter.transform().m11()) or 50.0

        painter.setRenderHint(painter.RenderHint.Antialiasing, True)

        pts = self._contour.points
        n = len(pts)
        if n < 2:
            return

        segments = list(range(n)) if self._contour.closed else list(range(n - 1))

        # Сначала все сегменты обычным цветом
        base_color = (
            self.LINE_COLOR_SELECTED
            if self.isSelected()
            else self.LINE_COLOR
        )
        pen_base = QPen(QColor(base_color), self.LINE_WIDTH)
        pen_base.setCosmetic(True)
        pen_base.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(pen_base)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self._path)

        # Поверх — выделенная грань
        if self._selected_edge_idx is not None and self._selected_edge_idx in segments:
            i = self._selected_edge_idx
            p1 = pts[i]
            p2 = pts[(i + 1) % n]

            pen = QPen(QColor(self.LINE_COLOR_SELECTED), self.LINE_WIDTH_SELECTED)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.drawLine(QPointF(*p1), QPointF(*p2))

        # И hover-грань (если не совпадает с выделенной)
        elif (
            self._hover_edge_idx is not None
            and self._hover_edge_idx in segments
            and self._hover_edge_idx != self._selected_edge_idx
        ):
            i = self._hover_edge_idx
            p1 = pts[i]
            p2 = pts[(i + 1) % n]

            pen = QPen(QColor(self.LINE_COLOR_HOVER), self.LINE_WIDTH_HOVER)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.drawLine(QPointF(*p1), QPointF(*p2))

    # ============================================================
    # REBUILD
    # ============================================================

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

    # ============================================================
    # EVENTS
    # ============================================================

    def _on_node_moved(self, idx: int, x: float, y: float) -> None:
        self._contour.set_point(idx, x, y)
        self._rebuild_path()
        self.changed.emit()

    def _find_edge_at(self, scene_x: float, scene_y: float) -> int | None:
        pts = self._contour.points
        n = len(pts)
        if n < 2:
            return None

        segments = range(n) if self._contour.closed else range(n - 1)

        best_dist = float("inf")
        best_idx: int | None = None

        for i in segments:
            p1 = pts[i]
            p2 = pts[(i + 1) % n]
            d, _ = dist_point_to_segment(
                scene_x, scene_y,
                p1[0], p1[1], p2[0], p2[1],
            )
            if d < best_dist:
                best_dist = d
                best_idx = i

        ppm = self._last_ppm or 50.0
        threshold_m = self.HIT_THRESHOLD_PX / ppm

        if best_dist <= threshold_m:
            return best_idx
        return None

    def mousePressEvent(self, event) -> None:
        """Клик по грани — выделить её. Клик по узлам сюда не доходит."""
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = event.scenePos()
            idx = self._find_edge_at(scene_pos.x(), scene_pos.y())

            if idx is not None:
                self._selected_edge_idx = idx
                self.update()
                event.accept()
                return

            # Клик мимо грани — снять выделение грани
            if self._selected_edge_idx is not None:
                self._selected_edge_idx = None
                self.update()

        super().mousePressEvent(event)

    def hoverMoveEvent(self, event) -> None:
        if not self._editable:
            super().hoverMoveEvent(event)
            return

        scene_pos = event.scenePos()
        idx = self._find_edge_at(scene_pos.x(), scene_pos.y())

        if idx != self._hover_edge_idx:
            self._hover_edge_idx = idx
            self.update()

        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        if self._hover_edge_idx is not None:
            self._hover_edge_idx = None
            self.update()
        super().hoverLeaveEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
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

    # ============================================================
    # EDITING
    # ============================================================

    def remove_node(self, idx: int) -> None:
        pts = self._contour.points
        if idx < 0 or idx >= len(pts):
            return
        if len(pts) <= 3:
            return

        pts.pop(idx)
        self._selected_edge_idx = None
        self._rebuild_nodes()
        self._rebuild_path()
        self.changed.emit()

    def insert_node_after_segment(self, seg_idx: int, t: float) -> int:
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
        self._selected_edge_idx = None
        self._rebuild_nodes()
        self._rebuild_path()
        self.changed.emit()
        return seg_idx + 1
