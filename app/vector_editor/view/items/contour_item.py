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
from .extra_node_item import ExtraNodeItem


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

    # Extra edges — визуально как main (по просьбе пользователя)
    EXTRA_COLOR = "#1A1A1A"           # как LINE_COLOR
    EXTRA_COLOR_SELECTED = "#0055CC"  # как LINE_COLOR_SELECTED
    EXTRA_WIDTH = 1.2                 # как LINE_WIDTH
    EXTRA_WIDTH_SELECTED = 2.5        # как LINE_WIDTH_SELECTED

    HIT_THRESHOLD_PX = 8.0

    def __init__(self, contour: VectorContour, parent=None):
        super().__init__(parent)

        self._contour = contour
        self._nodes: list[NodeItem] = []
        self._extra_nodes: list[ExtraNodeItem] = []
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
        self._rebuild_extra_nodes()
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
        for node in self._extra_nodes:
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
        self._rebuild_extra_nodes()
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

        # self._path уже содержит дуги — используем как есть
        path = QPainterPath(self._path)

        for a_id, b_id in self._contour.extra_edges:
            p1 = self._contour.get_point_by_id(a_id)
            p2 = self._contour.get_point_by_id(b_id)
            if p1 is None or p2 is None:
                continue
            path.moveTo(p1[0], p1[1])
            # Extra edges — тоже могут быть дугами
            self._segment_to(path, a_id, b_id, p1, p2)

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
            p1 = self._contour.get_point_by_id(a_id)
            p2 = self._contour.get_point_by_id(b_id)
            if p1 is None or p2 is None:
                continue

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
            elif is_hover:
                color = QColor(self.LINE_COLOR_HOVER)
                width = self.EXTRA_WIDTH_SELECTED
            else:
                color = QColor(self.EXTRA_COLOR)
                width = self.EXTRA_WIDTH

            style = Qt.PenStyle.SolidLine

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

    def _segment_to(self, path, a_id, b_id, p1, p2) -> None:
        """Добавить отрезок в path — прямой или дугу (по arcs)."""
        bulge = 0.0
        if a_id and b_id:
            bulge = self._contour.get_arc(a_id, b_id)

        if abs(bulge) < 1e-9:
            path.lineTo(p2[0], p2[1])
            return

        x1, y1 = p1
        x2, y2 = p2
        dx = x2 - x1
        dy = y2 - y1
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1e-9:
            path.lineTo(x2, y2)
            return

        # Середина
        mx = (x1 + x2) * 0.5
        my = (y1 + y2) * 0.5

        # Перпендикуляр (нормаль)
        nx = -dy / length
        ny = dx / length

        # Контрольная точка квадратичной Безье
        # C = M + 2 * perp * bulge * L
        k = 2.0 * bulge * length
        cx = mx + nx * k
        cy = my + ny * k

        path.quadTo(cx, cy, x2, y2)

    def _rebuild_path(self) -> None:
        self.prepareGeometryChange()

        path = QPainterPath()
        pts = self._contour.points
        n = len(pts)
        if not pts:
            self._path = path
            self.update()
            return

        node_ids = self._contour.node_ids

        path.moveTo(pts[0][0], pts[0][1])

        if self._contour.closed:
            for i in range(n):
                j = (i + 1) % n
                a_id = node_ids[i] if i < len(node_ids) else None
                b_id = node_ids[j] if j < len(node_ids) else None
                # Для замыкающего ребра path уже в точке pts[0]
                self._segment_to(path, a_id, b_id, pts[i], pts[j])
            # После quadTo к pts[0] path уже замкнут
            path.closeSubpath()
        else:
            for i in range(n - 1):
                a_id = node_ids[i] if i < len(node_ids) else None
                b_id = node_ids[i + 1] if i + 1 < len(node_ids) else None
                self._segment_to(path, a_id, b_id, pts[i], pts[i + 1])

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

    def _rebuild_extra_nodes(self) -> None:
        """Пересоздать ExtraNodeItem по current extra_points."""
        for node in self._extra_nodes:
            if node.scene() is not None:
                node.scene().removeItem(node)
            node.setParentItem(None)
        self._extra_nodes.clear()

        for nid, (x, y) in zip(
            self._contour.extra_node_ids,
            self._contour.extra_points,
        ):
            node = ExtraNodeItem(nid, x, y)
            node.setParentItem(self)
            node.node_moved.connect(self._on_extra_node_moved)
            node.drag_started.connect(self.node_drag_started.emit)
            node.drag_finished.connect(self.node_drag_finished.emit)
            node.setVisible(self._editable)
            self._extra_nodes.append(node)

    def _on_extra_node_moved(
        self, node_id: str, x: float, y: float,
    ) -> None:
        if self._contour.set_point_by_id(node_id, x, y):
            self._rebuild_path()
            self.changed.emit()

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
        for node in self._extra_nodes:
            node.setVisible(visible)

    def highlight_nodes(self, node_ids) -> None:
        wanted = set(node_ids)
        for node in self._nodes:
            node.set_highlight(node.node_id in wanted)
        for node in self._extra_nodes:
            node.set_highlight(node.node_id in wanted)

    def clear_highlight(self) -> None:
        for node in self._nodes:
            node.set_highlight(False)
        for node in self._extra_nodes:
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

    def prune_dangling_extra_nodes(self) -> int:
        """Удалить extra-узлы, не входящие ни в одно extra-ребро.

        Возвращает количество удалённых узлов.
        """
        used_ids: set[str] = set()
        for a_id, b_id in self._contour.extra_edges:
            used_ids.add(a_id)
            used_ids.add(b_id)

        # Оставляем extra-узлы, которые либо в extra_edge,
        # либо кто-то ещё на них ссылается. Main-узлы не трогаем.
        to_remove = [
            nid for nid in self._contour.extra_node_ids
            if nid not in used_ids
        ]

        for nid in to_remove:
            self._contour.remove_extra_point(nid)

        return len(to_remove)

    def _find_extra_edge_at(
        self, scene_x: float, scene_y: float,
    ) -> tuple[str, str] | None:
        """Найти extra-ребро под курсором. Возвращает пару node_ids."""
        best_dist = float("inf")
        best_edge: tuple[str, str] | None = None

        for edge in self._contour.extra_edges:
            a_id, b_id = edge
            p1 = self._contour.get_point_by_id(a_id)
            p2 = self._contour.get_point_by_id(b_id)
            if p1 is None or p2 is None:
                continue

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
        """Двойной клик — вставка узла.

        PRIORITY 1: extra-ребро → вставить extra-узел (не в main).
        PRIORITY 2: main-сегмент → вставить main-узел.
        """
        if not self._editable:
            super().mouseDoubleClickEvent(event)
            return

        scene_pos = event.scenePos()

        # PRIORITY 1: extra edge
        extra = self._find_extra_edge_at(
            scene_pos.x(), scene_pos.y(),
        )
        if extra is not None:
            self.mouseDoubleClickEvent_extra(event)
            event.accept()
            return

        # PRIORITY 2: main edge
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

    def mouseDoubleClickEvent_extra(self, event) -> None:
        """Двойной клик по extra-ребру → вставка extra-узла.

        Вызывается из основного mouseDoubleClickEvent ДО проверки
        main-рёбер. Добавляет новую extra-точку (не в main), при
        этом main-контур НЕ трогается.
        """
        scene_pos = event.scenePos()
        extra = self._find_extra_edge_at(
            scene_pos.x(), scene_pos.y(),
        )
        if extra is None:
            return

        a_id, b_id = extra
        pa = self._contour.get_point_by_id(a_id)
        pb = self._contour.get_point_by_id(b_id)
        if pa is None or pb is None:
            return

        _, t = dist_point_to_segment(
            scene_pos.x(), scene_pos.y(),
            pa[0], pa[1], pb[0], pb[1],
        )
        t = max(0.1, min(0.9, t))

        x = pa[0] + t * (pb[0] - pa[0])
        y = pa[1] + t * (pb[1] - pa[1])

        new_id = self._contour.add_extra_point(x, y)

        self._contour.remove_extra_edge(a_id, b_id)
        self._contour.add_extra_edge(a_id, new_id)
        self._contour.add_extra_edge(new_id, b_id)

        self._rebuild_extra_nodes()
        self._rebuild_path()
        self.update()
        self.changed.emit()

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
        self._rebuild_extra_nodes()
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
        self._rebuild_extra_nodes()
        self._rebuild_path()
        self.changed.emit()
        return seg_idx + 1
