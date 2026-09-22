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
SNAP_ANCHOR_COLOR = QColor("#FF3333")

# V9d: маркеры слотов (auto_rule группы)
SLOT_COLOR = QColor("#00B050")
SLOT_RADIUS_M = 0.08

# Совместимые пары (наш_tag, их_tag)
SNAP_PAIRS = frozenset({
    ("bottom", "top"),
    ("top", "bottom"),
})


class ComponentItem(QGraphicsObject):
    """QGraphicsObject-обёртка для Component."""

    # Эмитится после завершения drag или после apply_from_component
    moved = Signal()
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
        self._snap_to_ground = False
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

        # Anchor'ы — только у выделенного компонента
        if self.isSelected():
            anchors = self.anchors_local()
            if anchors:
                from PySide6.QtGui import QBrush as _QB, QColor as _QC
                ppm = abs(painter.transform().m11()) or 50.0
                r_m = 6.0 / ppm   # радиус ~6 пикселей в метрах

                for tag, (lx, ly) in anchors.items():
                    if tag == self._highlighted_anchor:
                        color = SNAP_ANCHOR_COLOR
                        pen_w = 2.4
                    else:
                        color = QColor("#FF6B00")
                        pen_w = 1.6

                    pen = QPen(color, pen_w)
                    pen.setCosmetic(True)
                    painter.setPen(pen)
                    painter.setBrush(QBrush(QColor("#FFFFFF")))
                    painter.drawEllipse(QPointF(lx, ly), r_m, r_m)

        # V9d: маркеры слотов (auto_rule) — только у выделенного
        if self.isSelected():
            slots = self.slots_local()
            if slots:
                ppm = abs(painter.transform().m11()) or 50.0
                slot_r = 5.0 / ppm  # ~5 пикселей экрана
                pen = QPen(SLOT_COLOR, 1.6)
                pen.setCosmetic(True)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                for key, (lx, ly) in slots.items():
                    painter.drawEllipse(
                        QPointF(lx, ly), slot_r, slot_r,
                    )

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

    def slot_y_from_bottom(self, slot_key: str) -> float | None:
        """V11: расстояние слота от низа контура (в метрах).

        Возвращает None, если слот не найден.
        """
        if self._path.isEmpty():
            return None
        slots = self.slots_local()
        pos = slots.get(slot_key)
        if pos is None:
            return None
        rect = self._path.boundingRect()
        # rect.bottom() = max_y = foundation (низ контура)
        # pos[1] — y слота в тех же (path) координатах.
        return rect.bottom() - pos[1]

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

    def slots_local(self) -> dict[str, tuple[float, float]]:
        """V9d-4d: слоты (auto_rule) — пересчитываются на лету
        с учётом param_overrides.

        Возвращает {slot_key: (x, y)} в ЛОКАЛЬНЫХ координатах item.
        Ключ вида "slot_<groupname>_<idx>".
        """
        if self._asset is None:
            return {}

        sg = getattr(self._asset, "semantic_groups", None) or {}
        rule_groups = [
            g for g in sg.values()
            if getattr(g, "auto_rule", None) and g.node_ids
        ]
        if not rule_groups:
            return {}

        # Позиции всех точек по id (main + extra), без override
        pts_by_id: dict[str, tuple[float, float]] = {}
        g_geom = self._asset.geometry or {}
        contour = g_geom.get("contour", [])
        node_ids = g_geom.get("node_ids", [])
        for i, nid in enumerate(node_ids):
            if i < len(contour):
                x, y = contour[i]
                pts_by_id[nid] = (float(x), float(y))
        extra_pts = g_geom.get("extra_points", [])
        extra_ids = g_geom.get("extra_node_ids", [])
        for i, nid in enumerate(extra_ids):
            if i < len(extra_pts):
                x, y = extra_pts[i]
                pts_by_id[nid] = (float(x), float(y))

        # Override-сдвиги по узлам
        overrides = getattr(self._component, "param_overrides", None) or {}
        deltas: dict[str, tuple[float, float]] = {}
        if overrides:
            params = getattr(self._asset, "parameters", None) or {}
            for p in params.values():
                ov = overrides.get(p.name)
                if ov is None:
                    continue
                shift = float(ov) - float(p.value)
                if abs(shift) < 1e-12:
                    continue
                nd = compute_delta_for_parameter(p, shift, sg)
                for nid, (dx, dy) in nd.items():
                    px, py = deltas.get(nid, (0.0, 0.0))
                    deltas[nid] = (px + dx, py + dy)

        def _pos(nid):
            p = pts_by_id.get(nid)
            if p is None:
                return None
            dx, dy = deltas.get(nid, (0.0, 0.0))
            return (p[0] + dx, p[1] + dy)

        def _centroid(group):
            xs, ys = [], []
            for nid in group.node_ids:
                pp = _pos(nid)
                if pp is None:
                    continue
                xs.append(pp[0])
                ys.append(pp[1])
            if not xs:
                return None
            return (sum(xs) / len(xs), sum(ys) / len(ys))

        result: dict[str, tuple[float, float]] = {}

        for group in rule_groups:
            rule = group.auto_rule
            axis = rule.get("axis", "y")
            axis_idx = 0 if axis == "x" else 1
            step = float(rule.get("step", 1.0))
            if abs(step) < 1e-9:
                continue

            # V9c-доп: все не-auto точки группы — независимые шаблоны
            templates: list = []
            for nid in group.node_ids:
                if not nid.startswith("e_auto_"):
                    p = _pos(nid)
                    if p is not None:
                        templates.append(p)
            if not templates:
                continue

            # Граница (until_group)
            until_name = rule.get("until_group") or ""
            limit_val = None
            if until_name:
                limit_group = None
                for gg in sg.values():
                    if gg.name == until_name:
                        limit_group = gg
                        break
                if limit_group is not None:
                    c = _centroid(limit_group)
                    if c is not None:
                        limit_val = c[axis_idx]

            max_count = int(rule.get("max_count", 30))

            # V15: вторая ось (сетка точек)
            axis2_name = rule.get("axis_x") or ""
            step2 = float(rule.get("step_x") or 0.0)
            until2_name = rule.get("until_group_x") or ""
            axis2_idx = None
            limit2_val = None
            if (axis2_name and abs(step2) > 1e-9 and until2_name):
                axis2_idx = 0 if axis2_name == "x" else 1
                if axis2_idx != axis_idx:
                    for gg in sg.values():
                        if gg.name == until2_name:
                            c = _centroid(gg)
                            if c is not None:
                                limit2_val = c[axis2_idx]
                            break
                    if limit2_val is None:
                        axis2_idx = None

            for tpl_idx, template_pos in enumerate(templates):
                # Базовая цепочка по первой оси
                chain1 = [tuple(template_pos)]
                if limit_val is not None:
                    cur = template_pos[axis_idx] + step
                    i1 = 0
                    while i1 < max_count:
                        if step > 0 and cur >= limit_val:
                            break
                        if step < 0 and cur <= limit_val:
                            break
                        pt = list(template_pos)
                        pt[axis_idx] = cur
                        chain1.append(tuple(pt))
                        cur += step
                        i1 += 1

                for i1, base_pt in enumerate(chain1):
                    # Базовая точка — старая схема ключа
                    key = f"slot_{group.id}_{tpl_idx}_{i1}"
                    result[key] = (
                        base_pt[0] - self._center_x,
                        base_pt[1] - self._center_y,
                    )

                    # Вторая ось (копии вбок)
                    if axis2_idx is None or limit2_val is None:
                        continue
                    cur2 = base_pt[axis2_idx] + step2
                    j = 1
                    while j <= max_count:
                        if step2 > 0 and cur2 >= limit2_val:
                            break
                        if step2 < 0 and cur2 <= limit2_val:
                            break
                        pt2 = list(base_pt)
                        pt2[axis2_idx] = cur2
                        key2 = (
                            f"slot_{group.id}_{tpl_idx}_{i1}_x{j}"
                        )
                        result[key2] = (
                            pt2[0] - self._center_x,
                            pt2[1] - self._center_y,
                        )
                        cur2 += step2
                        j += 1

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

    def slots_world(self) -> dict[str, tuple[float, float]]:
        """V9d-4: слоты (auto_rule) в scene-координатах."""
        from PySide6.QtCore import QPointF
        result = {}
        for key, (lx, ly) in self.slots_local().items():
            sp = self.mapToScene(QPointF(lx, ly))
            result[key] = (sp.x(), sp.y())
        return result

    def _try_snap(self) -> None:
        """Найти ближайший совместимый anchor и прилипнуть."""
        scene = self.scene()
        if scene is None:
            return

        # V14: к другим компонентам (anchor/slot) прилипают только
        # окна/двери/декор. Стены, башни, крыши — сами к себе
        # не цепляются, но могут прилипнуть к опорной линии.
        # V16: к другим компонентам прилипают "мелкие" элементы.
        # Определяем по типу ассета ИЛИ по имени компонента
        # (потому что окна часто имеют тип tower_body).
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

        my_world = self.anchors_world()
        if not my_world:
            self.clear_snap_highlight()
            self._component.clear_attachment()
            return

        views = scene.views()
        ppm = 50.0
        if views:
            ppm = abs(views[0].transform().m11()) or 50.0
        threshold_m = SNAP_THRESHOLD_PX / ppm

        best = None  # (dist, my_tag, their_item, their_tag, dx, dy)

        # V15: anchor-поиск идёт ВСЕГДА, но для не-attachable
        # допускаем только пару (bottom → top) — крыша/купол/башня
        # ставятся сверху. Остальные пары им запрещены.
        if True:
          for other in scene.items():
            if other is self:
                continue
            if not isinstance(other, ComponentItem):
                continue
            their_world = other.anchors_world()
            if not their_world:
                continue

            # Пропустить, если этот other уже привязан к НАМ (иначе цикл)
            other_comp_check = getattr(other, "_component", None)
            if (other_comp_check is not None
                    and other_comp_check.attach_to
                    == self._component.id):
                continue

            # V9d-4: окно НЕ привязываем к другому окну по anchor.
            # Окна цепляются только к слотам стен (или к не-окнам).
            my_type = getattr(self._asset, "type", "") if self._asset else ""
            their_type = (
                getattr(other._asset, "type", "")
                if other._asset else ""
            )
            if my_type == "window" and their_type == "window":
                continue

            for my_tag, (mx, my) in my_world.items():
                for their_tag, (tx, ty) in their_world.items():
                    if (my_tag, their_tag) not in SNAP_PAIRS:
                        continue
                    # V15: "встать сверху" (bottom→top) разрешено
                    # всем — крыша/купол/башня ставятся на стену.
                    # Другие пары (top→bottom) — только attachable.
                    if (not can_attach
                            and (my_tag, their_tag) != ("bottom", "top")):
                        continue
                    dx = tx - mx
                    dy = ty - my
                    dist = (dx * dx + dy * dy) ** 0.5
                    if dist <= threshold_m:
                        if best is None or dist < best[0]:
                            best = (dist, my_tag, other, their_tag,
                                    dx, dy)

        # V9d-4: поиск слотов (auto_rule) на соседних стенах.
        # Приоритет у слота — если он ближе, чем anchor-пара.
        best_slot = None
        my_bottom = my_world.get("bottom")
        if my_bottom is not None:
            mx, my = my_bottom

            # Собрать занятые слоты: {parent_comp_id: {slot_key, ...}}
            occupied: dict[str, set] = {}
            for cand in scene.items():
                if cand is self:
                    continue
                if not isinstance(cand, ComponentItem):
                    continue
                c_comp = getattr(cand, "_component", None)
                if c_comp is None or not c_comp.attach_to:
                    continue
                if c_comp.parent_anchor.startswith("slot_"):
                    occupied.setdefault(
                        c_comp.attach_to, set()
                    ).add(c_comp.parent_anchor)

            if not can_attach:
                pass
            else:
              for other in scene.items():
                if other is self:
                    continue
                if not isinstance(other, ComponentItem):
                    continue
                their_slots = other.slots_world()
                if not their_slots:
                    continue

                o_comp = getattr(other, "_component", None)
                if o_comp is None:
                    continue
                if o_comp.id == self._component.id:
                    continue
                # Пропустить, если other привязан к НАМ
                if o_comp.attach_to == self._component.id:
                    continue

                taken = occupied.get(o_comp.id, set())

                for slot_key, (sx, sy) in their_slots.items():
                    if slot_key in taken:
                        continue
                    dx = sx - mx
                    dy = sy - my
                    dist = (dx * dx + dy * dy) ** 0.5
                    if dist <= threshold_m:
                        if best_slot is None or dist < best_slot[0]:
                            best_slot = (
                                dist, "bottom", other, slot_key,
                                dx, dy,
                            )

        # Выбор: если слот ближе anchor-пары — берём слот
        if best_slot is not None:
            if best is None or best_slot[0] < best[0]:
                best = best_slot

        # V13: snap к опорной линии (ground line).
        # Если мой bottom anchor близко к Y линии — snap по Y.
        scene = self.scene()
        if scene is not None and hasattr(scene, "ground_line_y"):
            gy = scene.ground_line_y()
            if gy is not None and scene.ground_line_visible():
                my_bottom = my_world.get("bottom")
                if my_bottom is not None:
                    my_y = my_bottom[1]
                    dy = gy - my_y
                    if abs(dy) <= threshold_m:
                        # Если линия ближе, чем текущий best
                        if best is None or abs(dy) < best[0]:
                            best = (
                                abs(dy), "__ground__",
                                None, "__ground__",
                                0.0, dy,
                            )

        # V13: сброс флага — установится только если реально snap к ground
        self._snap_to_ground = False

        if best is None:
            self.clear_snap_highlight()
            return

        _, my_tag, other, their_tag, dx, dy = best

        # Сначала очищаем старую пару
        self.clear_snap_highlight()

        # V13: snap к ground line — сдвигаем только по Y,
        # attachment не создаём (это не компонент).
        if other is None:
            self.setPos(self.pos().x(), self.pos().y() + dy)
            self._component.x = self.pos().x()
            self._component.y = self.pos().y()
            self._snap_to_ground = True
            return

        # Сдвигаем себя на (dx, dy), чтобы наш anchor совпал с их
        self.setPos(self.pos().x() + dx, self.pos().y() + dy)

        # Подсветка
        self.set_highlighted_anchor(my_tag)
        other.set_highlighted_anchor(their_tag)

        # V11c: сохранить привязку в модель
        other_comp = getattr(other, "_component", None)
        if other_comp is not None:
            already = (
                self._component.attach_to == other_comp.id
                and self._component.attach_anchor == my_tag
                and self._component.parent_anchor == their_tag
            )
            if not already:
                self._component.set_attachment(
                    other_comp.id, my_tag, their_tag,
                )
                print(f"[SNAP] attach_to={other_comp.id} "
                      f"my={my_tag} their={their_tag}")
        self._snap_partner = other

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
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)
        self._try_snap()

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)

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
        self._snap_to_ground = False
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
