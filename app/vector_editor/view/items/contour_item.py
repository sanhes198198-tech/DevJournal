"""
ContourItem — QGraphicsObject, рисует замкнутый/разомкнутый контур.

Поддерживает:
  - узлы (NodeItem) — drag, delete;
  - грани (edges) — hover / selection / extrude;
  - двойной клик по main-сегменту → вставка узла;
  - extra_edges (V8-lite) — дополнительные рёбра между несоседними
    узлами, хранятся как пары node_ids.

Внутреннее состояние:
  - _selected_edge_idx: int | None — выделенная main-грань;
  - _hover_edge_idx: int | None — main-грань под курсором;
  - _selected_extra: tuple[str, str] | None — выделенное extra-ребро;
  - _hover_extra: tuple[str, str] | None — extra-ребро под курсором.

Приоритет при клике: Extra > Main.
Приоритет при hover:   Extra > Main.
Double-click: только main (extra не обрабатывается).
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor, QPainterPath, QPainterPathStroker, QPen,
)
from PySide6.QtWidgets import QGraphicsObject

from ...model.contour import VectorContour
from ...model.geometry import dist_point_to_segment
from ...model.operations import extrude_face
from .node_item import NodeItem


class ContourItem(QGraphicsObject):
    """Визуализация VectorContour."""

    changed = Signal()
    node_drag_started = Signal()
    node_drag_finished = Signal()

    LINE_WIDTH = 1.2
    LINE_WIDTH_SELECTED = 2.5
    LINE_WIDTH_HOVER = 2.0

    LINE_COLOR = "#1A1A1A"
    LINE_COLOR_SELECTED = "#0055CC"
    LINE_COLOR_HOVER = "#5588DD"

    # Extra edges — визуально отличаются от main
    EXTRA_COLOR = "#888888"
    EXTRA_COLOR_SELECTED = "#F28C28"   # оранжевый
    EXTRA_WIDTH = 1.8
    EXTRA_WIDTH_SELECTED = 3.2

    HIT_THRESHOLD_PX = 8.0

    def __init__(self, contour: VectorContour, parent=None):
        super().__init__(parent)

        self._contour = contour
        self._nodes: list[NodeItem] = []
        self._editable: bool = True
        self._last_ppm: float = 50.0

        self._selected_edge_idx: int | None = None
        self._hover_edge_idx: int | None = None

        self._selected_extra: tuple[str, str] | None = None
        self._hover_extra: tuple[str, str] | None = None

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

    def selected_extra(self) -> tuple[str, str] | None:
        return self._selected_extra

    def clear_edge_selection(self) -> None:
        changed = (
            self._selected_edge_idx is not None
            or self._selected_extra is not None
        )
        self._selected_edge_idx = None
        self._selected_extra = None
        if changed:
            self.update()

    def clear_extra_selection(self) -> None:
        if self._selected_extra is not None:
            self._selected_extra = None
            self.update()

    def set_editable(self, editable: bool) -> None:
        self._editable = editable
        for node in self._nodes:
            node.setVisible(editable)

    # ============================================================
    # EXTRUDE (по main-грани)
    # ============================================================

    def has_selected_edge(self) -> bool:
        return self._selected_edge_idx is not None

    def extrude_selected_face(self, distance: float) -> bool:
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
        self._selected_extra = None
        self._hover_extra = None

        self._rebuild_nodes()
        self._rebuild_path()
        self.changed.emit()
        return True

    # ============================================================
    # GEOMETRY
    # ============================================================

    def boundingRect(self) -> QRectF:
        if self._path.isEmpty():
            return QRectF()
        return self._path.boundingRect().adjusted(
            -1.0, -1.0, 1.0, 1.0
        )

    def shape(self) -> QPainterPath:
        """Форма для Qt-hit-test. Включает extra_edges, чтобы Qt
        корректно выбирал ContourItem при клике по extra."""
        ppm = self._last_ppm or 50.0
        stroke_w_m = max(self.HIT_THRESHOLD_PX / ppm, 0.01)

        stroker = QPainterPathStroker()
        stroker.setWidth(stroke_w_m)

        path = QPainterPath(self._path)

        for a_id, b_id in self._contour.extra_edges:
            ia = self._contour.index_of(a_id)
            ib = self._contour.index_of(b_id)
            if ia < 0 or ib < 0:
                continue
            ax, ay = self._contour.points[ia]
            bx, by = self._contour.points[ib]
            path.moveTo(ax, ay)
            path.lineTo(bx, by)

        return stroker.createStroke(path)

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

        segments = (
            list(range(n)) if self._contour.closed
            else list(range(n - 1))
        )

        # --- 1. Основной контур ---
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

        # --- 2. Extra edges (поверх main) ---
        for edge in self._contour.extra_edges:
            a_id, b_id = edge
            ia = self._contour.index_of(a_id)
            ib = self._contour.index_of(b_id)
            if ia < 0 or ib < 0:
                continue

            p1 = pts[ia]
            p2 = pts[ib]

            is_selected = (
                self._selected_extra is not None
                and frozenset(self._selected_extra)
                == frozenset(edge)
            )
            is_hover = (
                self._hover_extra is not None
                and frozenset(self._hover_extra)
                == frozenset(edge)
                and not is_selected
            )

            if is_selected:
                color = QColor(self.EXTRA_COLOR_SELECTED)
                width = self.EXTRA_WIDTH_SELECTED
                style = Qt.PenStyle.SolidLine
            elif is_hover:
                color = QColor(self.LINE_COLOR_HOVER)
                width = self.EXTRA_WIDTH_SELECTED
                style = Qt.PenStyle.SolidLine
            else:
                color = QColor(self.EXTRA_COLOR)
                width = self.EXTRA_WIDTH
                style = Qt.PenStyle.DashLine

            pen = QPen(color, width)
            pen.setCosmetic(True)
            pen.setStyle(style)
            painter.setPen(pen)
            painter.drawLine(QPointF(*p1), QPointF(*p2))

        # --- 3. Selected main edge (поверх всего) ---
        if (
            self._selected_edge_idx is not None
            and self._selected_edge_idx in segments
        ):
            i = self._selected_edge_idx
            p1 = pts[i]
            p2 = pts[(i + 1) % n]

            pen = QPen(
                QColor(self.LINE_COLOR_SELECTED),
                self.LINE_WIDTH_SELECTED,
            )
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.drawLine(QPointF(*p1), QPointF(*p2))

        # --- 4. Hover main edge (если не совпадает с selected) ---
        elif (
            self._hover_edge_idx is not None
            and self._hover_edge_idx in segments
            and self._hover_edge_idx != self._selected_edge_idx
        ):
            i = self._hover_edge_idx
            p1 = pts[i]
            p2 = pts[(i + 1) % n]

            pen = QPen(
                QColor(self.LINE_COLOR_HOVER),
                self.LINE_WIDTH_HOVER,
            )
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
            nid = self._contour.get_node_id(idx) or ""
            node = NodeItem(idx, x, y, node_id=nid)
            node.setParentItem(self)
            node.node_moved.connect(self._on_node_moved)
            node.drag_started.connect(self.node_drag_started.emit)
            node.drag_finished.connect(self.node_drag_finished.emit)
            node.setVisible(self._editable)
            self._nodes.append(node)

    # ============================================================
    # NODES VISIBILITY / HIGHLIGHT
    # ============================================================

    def are_nodes_visible(self) -> bool:
        if not self._nodes:
            return self._editable
        return self._nodes[0].isVisible()

    def set_nodes_visible(self, visible: bool) -> None:
        for node in self._nodes:
            node.setVisible(visible)

    def highlight_nodes(self, node_ids) -> None:
        wanted = set(node_ids)
        for node in self._nodes:
            node.set_highlight(node.node_id in wanted)

    def clear_highlight(self) -> None:
        for node in self._nodes:
            node.set_highlight(False)

    def _on_node_moved(self, idx: int, x: float, y: float) -> None:
        self._contour.set_point(idx, x, y)
        self._rebuild_path()
        self.changed.emit()

    # ============================================================
    # HIT-TEST: main edges
    # ============================================================

    def _find_edge_at(self, scene_x: float, scene_y: float) -> int | None:
        pts = self._contour.points
        n = len(pts)
        if n < 2:
            return None

        segments = (
            range(n) if self._contour.closed
            else range(n - 1)
        )

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

    # ============================================================
    # HIT-TEST: extra edges
    # ============================================================

    def _find_extra_edge_at(
        self, scene_x: float, scene_y: float,
    ) -> tuple[str, str] | None:
        """Найти extra-ребро под курсором. Возвращает пару node_ids."""
        best_dist = float("inf")
        best_edge: tuple[str, str] | None = None

        for edge in self._contour.extra_edges:
            a_id, b_id = edge
            ia = self._contour.index_of(a_id)
            ib = self._contour.index_of(b_id)
            if ia < 0 or ib < 0:
                continue

            p1 = self._contour.points[ia]
            p2 = self._contour.points[ib]

            d, _ = dist_point_to_segment(
                scene_x, scene_y,
                p1[0], p1[1], p2[0], p2[1],
            )
            if d < best_dist:
                best_dist = d
                best_edge = (a_id, b_id)

        ppm = self._last_ppm or 50.0
        threshold_m = self.HIT_THRESHOLD_PX / ppm

        if best_dist <= threshold_m:
            return best_edge
        return None

    # ============================================================
    # EVENTS
    # ============================================================

    def mousePressEvent(self, event) -> None:
        """Клик по грани — выделить. Приоритет: Extra > Main."""
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = event.scenePos()

            # PRIORITY 1: Extra
            extra = self._find_extra_edge_at(
                scene_pos.x(), scene_pos.y(),
            )
            if extra is not None:
                self._selected_extra = extra
                self._selected_edge_idx = None
                self.update()
                event.accept()
                return

            # PRIORITY 2: Main
            idx = self._find_edge_at(scene_pos.x(), scene_pos.y())
            if idx is not None:
                self._selected_edge_idx = idx
                self._selected_extra = None
                self.update()
                event.accept()
                return

            # Пусто внутри ContourItem
            changed = (
                self._selected_edge_idx is not None
                or self._selected_extra is not None
            )
            self._selected_edge_idx = None
            self._selected_extra = None
            if changed:
                self.update()

        super().mousePressEvent(event)

    def hoverMoveEvent(self, event) -> None:
        if not self._editable:
            super().hoverMoveEvent(event)
            return

        scene_pos = event.scenePos()

        extra = self._find_extra_edge_at(
            scene_pos.x(), scene_pos.y(),
        )

        idx = None
        if extra is None:
            idx = self._find_edge_at(
                scene_pos.x(), scene_pos.y(),
            )

        changed = (
            extra != self._hover_extra
            or idx != self._hover_edge_idx
        )
        self._hover_extra = extra
        self._hover_edge_idx = idx

        if changed:
            self.update()

        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        if (
            self._hover_edge_idx is not None
            or self._hover_extra is not None
        ):
            self._hover_edge_idx = None
            self._hover_extra = None
            self.update()

        super().hoverLeaveEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        """Двойной клик — вставка узла в main-сегмент.

        Extra НЕ обрабатывается (см. решение: функционал вставки
        точки в extra отложен до появления extra_only-узлов).
        """
        if not self._editable:
            super().mouseDoubleClickEvent(event)
            return

        scene_pos = event.scenePos()

        pts = self._contour.points
        n = len(pts)
        if n < 2:
            super().mouseDoubleClickEvent(event)
            return

        best_dist = float("inf")
        best_seg = -1
        best_t = 0.0

        segments = (
            range(n) if self._contour.closed
            else range(n - 1)
        )

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

        self._contour.remove_point(idx)
        self._selected_edge_idx = None
        self._selected_extra = None
        self._hover_edge_idx = None
        self._hover_extra = None
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

        self._contour.insert_point(seg_idx + 1, x, y)
        self._selected_edge_idx = None
        self._selected_extra = None
        self._rebuild_nodes()
        self._rebuild_path()
        self.changed.emit()
        return seg_idx + 1
