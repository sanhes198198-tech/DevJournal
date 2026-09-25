"""
ComponentItem — QGraphicsObject для одного Component.

Рисует контур ссылочного Asset'а (main + extra_edges).
Позиция/поворот/масштаб — из Component.
Сцена Y↑ (см. ConstructorCanvas.scale(ppm, -ppm)) — здесь
координаты в model-метрах без флипа.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject

from .param_handle_item import ParamHandleItem
from app.vector_editor.model.parameter import (
    compute_delta_for_parameter,
    apply_delta_to_points,
)


ASSET_LINE = QColor("#1A1A1A")
ASSET_LINE_SELECTED = QColor("#0055CC")
ORPHAN_COLOR = QColor("#CC3333")
LINE_WIDTH = 1.2
LINE_WIDTH_SELECTED = 2.0
ORPHAN_SIZE_M = 1.0

# Snap
SNAP_THRESHOLD_PX = 40.0

# V9d: маркеры слотов (auto_rule группы)

# Совместимые пары (наш_tag, их_tag)


LEGACY_SNAP_ENABLED = False  # A2: Pure Mount — legacy anchor/slot/ground отключены


class ComponentItem(QGraphicsObject):
    """QGraphicsObject-обёртка для Component."""

    # Эмитится после завершения drag или после apply_from_component
    moved = Signal()
    drag_started = Signal(str)  # comp_id, эмитится в mousePress
    # Двойной клик по composite — сигнал «войти» с asset_id
    enter_requested = Signal(str)
    # (comp_id, old_x, old_y, new_x, new_y) — после drag
    drag_finished = Signal(str, float, float, float, float)
    param_changed = Signal(str, str, float)

    MAX_DEPTH = 8

    def __init__(
        self, component, asset=None, registry=None, parent=None,
    ):
        super().__init__(parent)
        self._component = component
        self._asset = asset
        self._registry = registry
        self._path = QPainterPath()
        self._stroke_path = QPainterPath()  # V16: слои с fillable=False
        self._extra_path = QPainterPath()

        # Смещение контура, чтобы его ЦЕНТР был в (0,0).
        # Иначе башня рисуется сбоку от origin.
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._center_x = 0.0
        self._center_y = 0.0
        # Snap
        self._highlighted_anchor: str | None = None
        self._snap_partner = None
        # V13: флаг что snap был к ground line (не компоненту)
        # Undo: позиция до drag
        self._drag_old_pos = None
        # On-canvas handles
        self._handles: dict = {}

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges,
            True,
        )
        self.setZValue(3.0)
        self.setCacheMode(QGraphicsItem.CacheMode.NoCache)

        # Снап к 0.1 м при перемещении
        self._snap_step = 0.1

        self._rebuild_paths()
        self._apply_transform()

    # ------------------------------------------------------------

    @property
    def component(self):
        return self._component

    def set_asset(self, asset) -> None:
        self._asset = asset
        self.prepareGeometryChange()
        self._rebuild_paths()
        self.update()

    # ------------------------------------------------------------

    def _apply_transform(self) -> None:
        """Позиция/поворот/масштаб/layer из Component."""
        c = self._component
        self.setPos(c.x, c.y)
        self.setRotation(-c.rotation)
        self.setScale(c.scale)
        # Z от слоя: 100 + layer, чтобы не пересекаться с UI
        # V9-доп: окна +10 чтобы клик по ним ловился поверх стен
        self.setZValue(self._compute_z())

        # V12: если компонент заблокирован — нельзя тащить
        locked = bool(getattr(c, "locked", False))
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
            not locked,
        )

    def _compute_z(self) -> float:
        """Z из layer + бонус окнам (чтобы окна были поверх стен)."""
        c = self._component
        base = 100.0 + float(getattr(c, "layer", 0))
        asset_type = ""
        if self._asset is not None:
            asset_type = getattr(self._asset, "type", "")
        if asset_type == "window":
            base += 10.0
        return base

    # ------------------------------------------------------------

    def _clear_handles(self) -> None:
        for h in self._handles.values():
            h.setParentItem(None)
            if h.scene() is not None:
                h.scene().removeItem(h)
        self._handles.clear()

    def _rebuild_handles(self) -> None:
        self._clear_handles()
        if not self.isSelected():
            return
        if self._asset is None:
            return

        params = getattr(self._asset, "parameters", None) or {}
        if not params:
            return

        r = self._path.boundingRect()
        if not self._extra_path.isEmpty():
            er = self._extra_path.boundingRect()
            r = r.united(er)
        if r.isEmpty():
            return

        overrides = getattr(self._component, "param_overrides", None) or {}

        for p in params.values():
            if p.name == "height":
                base_v = float(p.value)
                cur_v = float(overrides.get("height", base_v))
                h = ParamHandleItem(
                    "height", "v", base_v, cur_v, parent=self,
                )
                h.setPos(r.right() + 0.8, r.center().y())
                h.value_changed.connect(self._on_handle_changed)
                self._handles["height"] = h
            elif p.name == "width":
                base_v = float(p.value)
                cur_v = float(overrides.get("width", base_v))
                h = ParamHandleItem(
                    "width", "h", base_v, cur_v, parent=self,
                )
                h.setPos(r.center().x(), r.bottom() + 0.8)
                h.value_changed.connect(self._on_handle_changed)
                self._handles["width"] = h

            # V15: ручки растяжения сторон
            elif p.name == "extend_right":
                base_v = float(p.value)
                cur_v = float(overrides.get("extend_right", base_v))
                h = ParamHandleItem(
                    "extend_right", "v", base_v, cur_v, parent=self,
                )
                # Справа от bbox, дальше чем height
                h.setPos(r.right() + 2.5, r.center().y())
                h.value_changed.connect(self._on_handle_changed)
                self._handles["extend_right"] = h
            elif p.name == "extend_left":
                base_v = float(p.value)
                cur_v = float(overrides.get("extend_left", base_v))
                h = ParamHandleItem(
                    "extend_left", "v", base_v, cur_v, parent=self,
                )
                h.setPos(r.left() - 0.8, r.center().y())
                h.value_changed.connect(self._on_handle_changed)
                self._handles["extend_left"] = h
            elif p.name == "extend_top":
                base_v = float(p.value)
                cur_v = float(overrides.get("extend_top", base_v))
                h = ParamHandleItem(
                    "extend_top", "h", base_v, cur_v, parent=self,
                )
                h.setPos(r.center().x(), r.top() - 0.8)
                h.value_changed.connect(self._on_handle_changed)
                self._handles["extend_top"] = h
            elif p.name == "extend_bottom":
                base_v = float(p.value)
                cur_v = float(overrides.get("extend_bottom", base_v))
                h = ParamHandleItem(
                    "extend_bottom", "h", base_v, cur_v, parent=self,
                )
                # Снизу от bbox, дальше чем width
                h.setPos(r.center().x(), r.bottom() + 2.5)
                h.value_changed.connect(self._on_handle_changed)
                self._handles["extend_bottom"] = h

    def _on_handle_changed(self, name: str, value: float) -> None:
        self.param_changed.emit(self._component.id, name, value)

    def _rebuild_paths(self) -> None:
        self._path = QPainterPath()
        self._stroke_path = QPainterPath()
        self._extra_path = QPainterPath()

        if self._asset is None:
            return

        # V16: сборка возвращает 4 пути —
        # fill (заливается), stroke (только контур),
        # extra (рёбра), center.
        overrides = getattr(self._component, "param_overrides", None) or {}
        fill, stroke, extra, center = self._collect_asset_paths(
            self._asset, depth=0, param_overrides=overrides,
        )
        self._path = fill
        self._stroke_path = stroke
        self._extra_path = extra
        self._center_x, self._center_y = center

    def _collect_asset_paths(
        self, asset, depth: int, param_overrides: dict | None = None,
    ) -> tuple[
        QPainterPath, QPainterPath, QPainterPath, tuple[float, float]
    ]:
        """V16: собрать пути из asset'а рекурсивно.

        Возвращает (fill_path, stroke_path, extra_path, (cx, cy)):
          - fill_path   — слои с fillable=True (заливаются текстурой)
          - stroke_path — слои с fillable=False (только контур)
          - extra_path  — extra-рёбра всех слоёв
          - center      — центр bbox первого слоя (для anchor'ов)
        """
        fill = QPainterPath()
        stroke = QPainterPath()
        extra = QPainterPath()

        if asset is None:
            return fill, stroke, extra, (0.0, 0.0)

        if depth > self.MAX_DEPTH:
            return fill, stroke, extra, (0.0, 0.0)

        # V16: список слоёв. Старые ассеты без layers →
        # единственный fillable-слой из asset.geometry.
        layer_items: list[tuple[dict, bool]] = []
        asset_layers = getattr(asset, "layers", None) or []
        if asset_layers:
            for layer in asset_layers:
                if not getattr(layer, "visible", True):
                    continue
                layer_items.append((
                    layer.geometry or {},
                    bool(getattr(layer, "fillable", True)),
                ))
        else:
            layer_items.append((asset.geometry, True))

        if not layer_items:
            # Все слои скрыты
            return fill, stroke, extra, (0.0, 0.0)

        # Для центра берём ПЕРВЫЙ слой
        first_geo, _ = layer_items[0]
        orig_contour = list(first_geo.get("contour", []))

        for layer_geo, fillable in layer_items:
            contour = list(layer_geo.get("contour", []))
            node_ids = list(layer_geo.get("node_ids", []))
            extra_pts = list(layer_geo.get("extra_points", []))
            extra_ids = list(layer_geo.get("extra_node_ids", []))
            extra_edges = layer_geo.get("extra_edges", [])

            # --- Override параметров ---
            if param_overrides:
                params = getattr(asset, "parameters", None) or {}
                sem_groups = getattr(asset, "semantic_groups", None) or {}
                for p in params.values():
                    ov = param_overrides.get(p.name)
                    if ov is None:
                        continue
                    delta_shift = float(ov) - float(p.value)
                    if abs(delta_shift) < 1e-12:
                        continue
                    node_delta = compute_delta_for_parameter(
                        p, delta_shift, sem_groups,
                    )
                    contour = apply_delta_to_points(
                        contour, node_ids, node_delta,
                    )
                    extra_pts = apply_delta_to_points(
                        extra_pts, extra_ids, node_delta,
                    )

            # --- Arcs ---
            arcs_map: dict[tuple, float] = {}
            for arc in layer_geo.get("arcs", []) or []:
                if not isinstance(arc, (list, tuple)) or len(arc) < 3:
                    continue
                try:
                    bv = float(arc[2])
                except (TypeError, ValueError):
                    continue
                if abs(bv) < 1e-9:
                    continue
                arcs_map[(str(arc[0]), str(arc[1]))] = bv

            def _get_bulge(a_id, b_id, _m=arcs_map):
                if not a_id or not b_id:
                    return 0.0
                v = _m.get((a_id, b_id))
                if v is not None:
                    return v
                v = _m.get((b_id, a_id))
                if v is not None:
                    return v
                return 0.0

            def _append_segment(path, p1, p2, a_id, b_id):
                bulge = _get_bulge(a_id, b_id)
                if abs(bulge) < 1e-9:
                    path.lineTo(float(p2[0]), float(p2[1]))
                    return
                x1, y1 = float(p1[0]), float(p1[1])
                x2, y2 = float(p2[0]), float(p2[1])
                dx = x2 - x1
                dy = y2 - y1
                L = (dx * dx + dy * dy) ** 0.5
                if L < 1e-9:
                    path.lineTo(x2, y2)
                    return
                mx = (x1 + x2) * 0.5
                my = (y1 + y2) * 0.5
                nx = -dy / L
                ny = dx / L
                k = 2.0 * bulge * L
                cx = mx + nx * k
                cy = my + ny * k
                path.quadTo(cx, cy, x2, y2)

            # --- Целевой path по fillable ---
            target = fill if fillable else stroke

            # --- Main контур этого слоя ---
            n_pts = len(contour)
            n_ids = len(node_ids)
            if n_pts >= 2:
                x0, y0 = contour[0]
                target.moveTo(float(x0), float(y0))
                for i in range(1, n_pts):
                    p1 = contour[i - 1]
                    p2 = contour[i]
                    a_id = node_ids[i - 1] if (i - 1) < n_ids else None
                    b_id = node_ids[i] if i < n_ids else None
                    _append_segment(target, p1, p2, a_id, b_id)
                if layer_geo.get("closed", True):
                    p1 = contour[n_pts - 1]
                    p2 = contour[0]
                    a_id = (
                        node_ids[n_pts - 1]
                        if (n_pts - 1) < n_ids else None
                    )
                    b_id = node_ids[0] if n_ids > 0 else None
                    _append_segment(target, p1, p2, a_id, b_id)
                    target.closeSubpath()

            # --- Extra edges этого слоя → в общий extra ---
            pos_map: dict[str, tuple[float, float]] = {}
            for i, nid in enumerate(node_ids):
                if i < len(contour):
                    x, y = contour[i]
                    pos_map[nid] = (float(x), float(y))
            for i, nid in enumerate(extra_ids):
                if i < len(extra_pts):
                    x, y = extra_pts[i]
                    pos_map[nid] = (float(x), float(y))

            for edge in extra_edges:
                if not isinstance(edge, (list, tuple)) or len(edge) != 2:
                    continue
                a_id, b_id = edge
                pa = pos_map.get(a_id)
                pb = pos_map.get(b_id)
                if pa is None or pb is None:
                    continue
                extra.moveTo(pa[0], pa[1])
                extra.lineTo(pb[0], pb[1])

        # --- Вложенные компоненты (рекурсия) ---
        comps = getattr(asset, "components", {})
        if comps and self._registry is not None:
            from PySide6.QtGui import QTransform
            for comp in comps.values():
                sub = self._registry.get(comp.asset_id)
                if sub is None:
                    continue
                sub_fill, sub_stroke, sub_extra, _ = (
                    self._collect_asset_paths(
                        sub, depth + 1,
                        param_overrides=comp.param_overrides,
                    )
                )
                t = QTransform()
                t.translate(comp.x, comp.y)
                t.rotate(-comp.rotation)
                t.scale(comp.scale, comp.scale)
                if not sub_fill.isEmpty():
                    fill.addPath(t.map(sub_fill))
                if not sub_stroke.isEmpty():
                    stroke.addPath(t.map(sub_stroke))
                if not sub_extra.isEmpty():
                    extra.addPath(t.map(sub_extra))

        # --- Центрирование по bbox первого слоя ---
        if orig_contour:
            xs = [float(p[0]) for p in orig_contour]
            ys = [float(p[1]) for p in orig_contour]
            cx = (min(xs) + max(xs)) / 2
            cy = (min(ys) + max(ys)) / 2
            from PySide6.QtGui import QTransform
            shift = QTransform()
            shift.translate(-cx, -cy)
            fill = shift.map(fill)
            stroke = shift.map(stroke)
            extra = shift.map(extra)
            return fill, stroke, extra, (cx, cy)

        return fill, stroke, extra, (0.0, 0.0)

    def boundingRect(self) -> QRectF:
        if self._asset is None:
            return QRectF(
                0, 0, ORPHAN_SIZE_M, ORPHAN_SIZE_M,
            )

        r = QRectF()
        if not self._path.isEmpty():
            r = self._path.boundingRect()
        if not self._extra_path.isEmpty():
            er = self._extra_path.boundingRect()
            r = r.united(er) if not r.isEmpty() else er

        if r.isEmpty():
            return QRectF()
        # Запас: 0.3 м обычный + 2.5 м при выделении (для подписей размеров)
        pad = 2.5 if self.isSelected() else 0.3
        return r.adjusted(-pad, -pad, pad, pad)

    def shape(self) -> QPainterPath:
        """V16: кликабельный bbox — тело компонента захватывается
        в любой точке, а не только по контуру."""
        result = QPainterPath()
        if self._path.isEmpty() and self._extra_path.isEmpty():
            return result

        r = QRectF()
        if not self._path.isEmpty():
            r = self._path.boundingRect()
        if not self._extra_path.isEmpty():
            er = self._extra_path.boundingRect()
            r = r.united(er) if not r.isEmpty() else er
        if not r.isEmpty():
            result.addRect(r)
        return result

    def paint(self, painter, option, widget=None) -> None:
        painter.setRenderHint(painter.RenderHint.Antialiasing, True)

        # Orphan
        if self._asset is None:
            pen = QPen(ORPHAN_COLOR, 1.5)
            pen.setCosmetic(True)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            r = QRectF(0, 0, ORPHAN_SIZE_M, ORPHAN_SIZE_M)
            painter.drawRect(r)
            painter.drawLine(
                QPointF(r.left(), r.top()),
                QPointF(r.right(), r.bottom()),
            )
            painter.drawLine(
                QPointF(r.right(), r.top()),
                QPointF(r.left(), r.bottom()),
            )
            return

        if self.isSelected():
            color = ASSET_LINE_SELECTED
            width = LINE_WIDTH_SELECTED
        else:
            color = ASSET_LINE
            width = LINE_WIDTH

        pen = QPen(color, width)
        pen.setCosmetic(True)
        painter.setPen(pen)

        # V11: заливка. Приоритет:
        #   1) fill_pattern (текстура) — если задана
        #   2) filled=True — белый
        #   3) иначе — без заливки (только контур)
        from PySide6.QtGui import QBrush as _QB

        pattern = str(
            getattr(self._component, "fill_pattern", "") or ""
        )
        filled = bool(getattr(self._component, "filled", False))

        if pattern == "hatch":
            painter.setBrush(_QB(
                QColor("#999999"),
                Qt.BrushStyle.BDiagPattern,
            ))
        elif pattern == "diamonds":
            painter.setBrush(_QB(
                QColor("#444444"),
                Qt.BrushStyle.DiagCrossPattern,
            ))
        elif filled:
            painter.setBrush(QBrush(QColor("#FFFFFF")))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)

        if not self._path.isEmpty():
            painter.drawPath(self._path)

        # V16: stroke-only (слои с fillable=False) —
        # только перо, без заливки. Рамы поверх окон.
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if not self._stroke_path.isEmpty():
            painter.drawPath(self._stroke_path)

        if not self._extra_path.isEmpty():
            painter.drawPath(self._extra_path)

        # Габариты (B) — только у выделенного
        if self.isSelected():
            self._paint_dimensions(painter)

    def _paint_dimensions(self, painter) -> None:
        """Подписи ширины/высоты в экранных пикселях (только у выделенного)."""
        r = QRectF()
        if not self._path.isEmpty():
            r = self._path.boundingRect()
        if not self._extra_path.isEmpty():
            er = self._extra_path.boundingRect()
            r = r.united(er) if not r.isEmpty() else er
        if r.isEmpty():
            return

        w = r.width()
        h = r.height()

        scene = self.scene()
        if scene is None:
            return
        views = scene.views()
        if not views:
            return
        view = views[0]

        # Точки в scene-координатах
        bottom_scene = self.mapToScene(
            QPointF(r.center().x(), r.bottom())
        )
        right_scene = self.mapToScene(
            QPointF(r.right(), r.center().y())
        )

        # Переводим в пиксели viewport
        bottom_px = view.mapFromScene(bottom_scene)
        right_px = view.mapFromScene(right_scene)

        from PySide6.QtGui import QFont, QFontMetrics

        painter.save()
        painter.resetTransform()  # отключаем масштаб сцены

        font = QFont("sans-serif")
        font.setPixelSize(12)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#0055CC")))

        fm = QFontMetrics(font)

        # Ширина — снизу по центру
        w_text = f"{w:.2f} м"
        w_tw = fm.horizontalAdvance(w_text)
        painter.drawText(
            QPointF(bottom_px.x() - w_tw / 2, bottom_px.y() + 16),
            w_text,
        )

        # Высота — справа
        h_text = f"{h:.2f} м"
        painter.drawText(
            QPointF(right_px.x() + 8, right_px.y() + 4),
            h_text,
        )

        painter.restore()

    # ------------------------------------------------------------

    def apply_from_component(self) -> None:
        """Пересобрать transform из компонента (после правки в панели)."""
        c = self._component
        self.setPos(c.x, c.y)
        self.setRotation(-c.rotation)
        self.setScale(c.scale)
        self.setZValue(self._compute_z())
        self.update()
        self.moved.emit()

    def wall_height_m(self) -> float:
        """V11: высота контура в метрах (уже с override).

        Возвращает 0.0, если контур пуст.
        """
        if self._path.isEmpty():
            return 0.0
        return self._path.boundingRect().height()

    def anchors_local(self) -> dict[str, tuple[float, float]]:
        """Anchor'ы ссылочного asset'а в ЛОКАЛЬНЫХ координатах item.

        V11b: учитывает param_overrides — anchor-точки тоже сдвигаются,
        когда контур растянут через параметры.
        """
        if self._asset is None:
            return {}

        raw = self._asset.anchors()
        if not raw:
            return {}

        # Собрать суммарную дельту по узлам от override-параметров
        overrides = getattr(self._component, "param_overrides", None) or {}
        deltas_per_node: dict[str, tuple[float, float]] = {}

        if overrides:
            params = getattr(self._asset, "parameters", None) or {}
            sg_all = getattr(self._asset, "semantic_groups", None) or {}
            for p in params.values():
                ov = overrides.get(p.name)
                if ov is None:
                    continue
                shift = float(ov) - float(p.value)
                if abs(shift) < 1e-12:
                    continue
                nd = compute_delta_for_parameter(p, shift, sg_all)
                for nid, (dx, dy) in nd.items():
                    px, py = deltas_per_node.get(nid, (0.0, 0.0))
                    deltas_per_node[nid] = (px + dx, py + dy)

        sg = getattr(self._asset, "semantic_groups", None) or {}

        result = {}
        for tag, (x, y) in raw.items():
            avg_dx = 0.0
            avg_dy = 0.0

            # V15: сначала ищем группу anchor_<tag> (например,
            # anchor_top), и только если её нет — <tag> (top).
            # Так якорь не едет вместе с "чужими" узлами, которые
            # попали в другую группу (right/left/top).
            group = None
            for g in sg.values():
                if g.name == f"anchor_{tag}":
                    group = g
                    break
            if group is None:
                for g in sg.values():
                    if g.name == tag:
                        group = g
                        break

            if group is not None and group.node_ids:
                dxs, dys = [], []
                for nid in group.node_ids:
                    d = deltas_per_node.get(nid)
                    if d is not None:
                        dxs.append(d[0])
                        dys.append(d[1])
                if dxs:
                    avg_dx = sum(dxs) / len(dxs)
                    avg_dy = sum(dys) / len(dys)

            result[tag] = (
                x + avg_dx - self._center_x,
                y + avg_dy - self._center_y,
            )

        return result

    def set_highlighted_anchor(self, tag: str | None) -> None:
        if self._highlighted_anchor != tag:
            self._highlighted_anchor = tag
            self.update()

    def clear_snap_highlight(self) -> None:
        self.set_highlighted_anchor(None)
        partner = self._snap_partner
        self._snap_partner = None
        if partner is not None and partner is not self:
            partner.set_highlighted_anchor(None)

    def anchors_world(self) -> dict[str, tuple[float, float]]:
        """Anchor'ы в scene-координатах (с учётом transform)."""
        from PySide6.QtCore import QPointF
        result = {}
        for tag, (lx, ly) in self.anchors_local().items():
            sp = self.mapToScene(QPointF(lx, ly))
            result[tag] = (sp.x(), sp.y())
        return result

    # ============================================================
    # V22 (Mounting): MountPoint locations
    # ============================================================

    def _asset_bbox(self):
        """Локальный bbox asset по всем видимым слоям.

        Возвращает (xmin, ymin, xmax, ymax) или None.
        """
        if self._asset is None:
            return None

        xs, ys = [], []
        layers = getattr(self._asset, "layers", None) or []
        geometries = []
        if layers:
            for layer in layers:
                if not getattr(layer, "visible", True):
                    continue
                geometries.append(layer.geometry or {})
        if not geometries:
            geometries = [getattr(self._asset, "geometry", {}) or {}]

        for g in geometries:
            contour = g.get("contour", []) or []
            for p in contour:
                xs.append(p[0])
                ys.append(p[1])
            extra = g.get("extra_points", []) or []
            for p in extra:
                xs.append(p[0])
                ys.append(p[1])

        if not xs:
            return None
        return (min(xs), min(ys), max(xs), max(ys))

    def mount_locations_local(self) -> dict:
        """Развернуть asset.mountpoints в локальные координаты item.

        Возвращает {mp_id: [(ix, iy, role_str, lx, ly), ...]}.
        role_str — "window"/"door"/... или None.
        Координаты lx/ly — в системе item (минус _center_x/y).
        """
        if self._asset is None:
            return {}

        mps = getattr(self._asset, "mountpoints", None) or []
        if not mps:
            return {}

        result: dict = {}
        bbox = self._asset_bbox()
        for mp in mps:
            try:
                locs = mp.resolve(bbox=bbox)
            except Exception:
                continue
            arr = []
            for loc in locs:
                lx = loc.position[0] - self._center_x
                ly = loc.position[1] - self._center_y
                # role может быть MountRole или str
                role_str = None
                if loc.role:
                    role_str = getattr(
                        loc.role, "value", str(loc.role),
                    )
                arr.append((
                    loc.index_x, loc.index_y, role_str,
                    float(lx), float(ly),
                ))
            result[mp.id] = arr
        return result

    def mount_locations_world(self) -> dict:
        """То же, но в scene-координатах.

        Возвращает {mp_id: [(ix, iy, role_str, sx, sy), ...]}.
        """
        local = self.mount_locations_local()
        result: dict = {}
        for mp_id, arr in local.items():
            world_arr = []
            for ix, iy, role_str, lx, ly in arr:
                sp = self.mapToScene(QPointF(lx, ly))
                world_arr.append((
                    ix, iy, role_str,
                    float(sp.x()), float(sp.y()),
                ))
            result[mp_id] = world_arr
        return result

    def mount_locations_by_role(self, role: str) -> list:
        """Все mount locations с указанной ролью в scene-координатах.

        Возвращает [(mp_id, ix, iy, sx, sy), ...].
        """
        if not role:
            return []
        result = []
        world = self.mount_locations_world()
        for mp_id, arr in world.items():
            for ix, iy, r, sx, sy in arr:
                if r == role:
                    result.append((mp_id, ix, iy, sx, sy))
        return result

    def _try_snap(self) -> None:
        """Найти ближайший MountLocation с подходящей ролью и прилипнуть.

        Логика поиска вынесена в snap_resolver.find_mount_snap().
        Здесь — только подготовка (can_attach, threshold) и применение.
        """
        scene = self.scene()
        if scene is None:
            return

        # Снапится только окно/дверь/декор. Тип asset — window/door/ornament,
        # либо имя содержит okno/окно/door/двер.
        ATTACHABLE = ("window", "door", "ornament")
        _mt = getattr(self._asset, "type", "") if self._asset else ""
        _name_lower = (
            getattr(self._component, "name", "") or ""
        ).lower()
        _name_ok = (
            "okno" in _name_lower
            or "окно" in _name_lower
            or "door" in _name_lower
            or "двер" in _name_lower
        )
        can_attach = (_mt in ATTACHABLE) or _name_ok

        _role = getattr(self._component, "role", None)
        _role_str = _role.value if _role else None

        if not (can_attach and _role_str):
            self.clear_snap_highlight()
            self._pending_snap = None
            return

        my_world = self.anchors_world()
        my_bottom = my_world.get("bottom")
        if my_bottom is None:
            self.clear_snap_highlight()
            self._pending_snap = None
            return

        views = scene.views()
        ppm = 50.0
        if views:
            ppm = abs(views[0].transform().m11()) or 50.0
        threshold_m = SNAP_THRESHOLD_PX / ppm

        from ...snap_resolver import find_mount_snap
        result = find_mount_snap(
            scene, self, my_bottom, _role_str, threshold_m,
            ComponentItem,
        )

        if result is None:
            self.clear_snap_highlight()
            self._pending_snap = None
            return

        # Сначала очищаем старую пару
        self.clear_snap_highlight()

        # Сдвигаем себя на (dx, dy), чтобы наш anchor совпал с их
        self.setPos(
            self.pos().x() + result.dx,
            self.pos().y() + result.dy,
        )

        # Подсветка
        self.set_highlighted_anchor(result.my_tag)
        result.other_item.set_highlighted_anchor(result.their_tag)

        # V21: candidate сохраняем, attachment коммитим на mouseRelease.
        other_comp = getattr(result.other_item, "_component", None)
        if other_comp is not None:
            self._pending_snap = (
                other_comp.id, result.my_tag, result.their_tag,
            )
        self._snap_partner = result.other_item

    def mouseDoubleClickEvent(self, event) -> None:
        """Двойной клик — войти в composite (если это composite)."""
        if self._asset is not None:
            comps = getattr(self._asset, "components", None)
            if comps:
                self.enter_requested.emit(self._asset.id)
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_old_pos = (self.pos().x(), self.pos().y())
            # V21: сброс pending — новый drag начинается с нуля
            self._pending_snap = None
            # Phase 13+: уведомить окно — снять снапшот для undo reflow
            self.drag_started.emit(self._component.id)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)
        self._try_snap()

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)

        # V21: commit pending attachment — snap во время drag был preview.
        pending = getattr(self, "_pending_snap", None)
        if pending is not None:
            pid, my_t, their_t = pending
            already = (
                self._component.attach_to == pid
                and self._component.attach_anchor == my_t
                and self._component.parent_anchor == their_t
            )
            if not already:
                self._component.set_attachment(pid, my_t, their_t)
                _kind = (
                    "mount" if their_t.startswith("mp_")
                    else "anchor"
                )
                print(f"[SNAP-COMMIT] attach_to={pid} "
                      f"my={my_t} their={their_t} kind={_kind}")
            self._pending_snap = None

        # Если компонент привязан к родителю через anchor —
        # позицией управляет reflow, не трогаем её руками.
        # Иначе любой клик сдвигал бы точку стыковки.
        attached = bool(getattr(self._component, "attach_to", ""))

        if attached:
            pos = self.pos()
            sx = pos.x()
            sy = pos.y()
        elif self._snap_partner is not None:
            # Сработал snap — не округляем, точная позиция
            pos = self.pos()
            sx = pos.x()
            sy = pos.y()
        else:
            # Свободный компонент — снапим к сетке 0.1 м
            pos = self.pos()
            step = self._snap_step
            sx = round(pos.x() / step) * step
            sy = round(pos.y() / step) * step

            if abs(sx - pos.x()) > 1e-9 or abs(sy - pos.y()) > 1e-9:
                self.setPos(sx, sy)

        # Записываем в компонент
        self._component.x = sx
        self._component.y = sy
        self.moved.emit()

        # Undo: если позиция изменилась — сигнал для команды
        if self._drag_old_pos is not None:
            ox, oy = self._drag_old_pos
            if abs(ox - sx) > 1e-6 or abs(oy - sy) > 1e-6:
                self.drag_finished.emit(
                    self._component.id, ox, oy, sx, sy,
                )
            self._drag_old_pos = None

        # Убираем подсветку snap
        self.clear_snap_highlight()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.prepareGeometryChange()
            self.update()
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, self._rebuild_handles)
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # V12: при drag — эмитим moved на каждое изменение позиции,
            # чтобы дети (окна на слотах) двигались синхронно.
            if self._drag_old_pos is not None:
                self.moved.emit()
        return super().itemChange(change, value)
