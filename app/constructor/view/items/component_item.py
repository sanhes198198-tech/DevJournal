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
    # (comp_id, param_name, value) — с on-canvas handles
    param_changed = Signal(str, str, float)
    # (comp_id, old_x, old_y, new_x, new_y) — после drag
    drag_finished = Signal(str, float, float, float, float)

    MAX_DEPTH = 8

    def __init__(
        self, component, asset=None, registry=None, parent=None,
    ):
        super().__init__(parent)
        self._component = component
        self._asset = asset
        self._registry = registry
        self._path = QPainterPath()
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
        # On-canvas слайдеры параметров (создаются при выделении)
        self._handles: dict = {}
        # Undo: позиция до drag
        self._drag_old_pos = None

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
        self.setZValue(100.0 + float(getattr(c, "layer", 0)))

    # ------------------------------------------------------------

    def _clear_handles(self) -> None:
        for h in self._handles.values():
            h.setParentItem(None)
            if h.scene() is not None:
                h.scene().removeItem(h)
        self._handles.clear()

    def _rebuild_handles(self) -> None:
        """Создать/обновить on-canvas слайдеры (только у выделенного)."""
        self._clear_handles()

        if not self.isSelected():
            return
        if self._asset is None:
            return

        params = getattr(self._asset, "parameters", None) or {}
        if not params:
            return

        # bbox базовой геометрии (без padding boundingRect)
        r = self._path.boundingRect()
        if not self._extra_path.isEmpty():
            er = self._extra_path.boundingRect()
            r = r.united(er)
        if r.isEmpty():
            return

        overrides = getattr(self._component, "param_overrides", None) or {}

        # Высота — вертикальный справа
        h_param = None
        for p in params.values():
            if p.name == "height":
                h_param = p
                break
        if h_param is not None:
            base_v = float(h_param.value)
            cur_v = float(overrides.get("height", base_v))
            h = ParamHandleItem(
                "height", "v", base_v, cur_v, parent=self,
            )
            h.setPos(r.right() + 0.8, r.center().y())
            h.value_changed.connect(self._on_handle_changed)
            self._handles["height"] = h

        # Ширина — горизонтальный снизу
        w_param = None
        for p in params.values():
            if p.name == "width":
                w_param = p
                break
        if w_param is not None:
            base_v = float(w_param.value)
            cur_v = float(overrides.get("width", base_v))
            h = ParamHandleItem(
                "width", "h", base_v, cur_v, parent=self,
            )
            h.setPos(r.center().x(), r.bottom() + 0.8)
            h.value_changed.connect(self._on_handle_changed)
            self._handles["width"] = h

    def _on_handle_changed(self, name: str, value: float) -> None:
        self.param_changed.emit(self._component.id, name, value)

    def _rebuild_paths(self) -> None:
        self._path = QPainterPath()
        self._extra_path = QPainterPath()

        if self._asset is None:
            return

        # Рекурсивная сборка (центрирование внутри)
        overrides = getattr(self._component, "param_overrides", None) or {}
        main, extra, center = self._collect_asset_paths(
            self._asset, depth=0, param_overrides=overrides,
        )
        self._path = main
        self._extra_path = extra
        # Запоминаем центр bbox — он же используется для anchor'ов
        self._center_x, self._center_y = center

    def _collect_asset_paths(
        self, asset, depth: int, param_overrides: dict | None = None,
    ) -> tuple[QPainterPath, QPainterPath, tuple[float, float]]:
        """Собрать main + extra из asset'а рекурсивно.

        Возвращает (main_path, extra_path, (cx, cy)) — центр bbox,
        на который пути смещены.
        """
        main = QPainterPath()
        extra = QPainterPath()

        if asset is None:
            return main, extra, (0.0, 0.0)

        if depth > self.MAX_DEPTH:
            return main, extra, (0.0, 0.0)

        g = asset.geometry
        contour = list(g.get("contour", []))
        orig_contour = list(contour)  # база для центра (до override)
        node_ids = list(g.get("node_ids", []))
        extra_pts = list(g.get("extra_points", []))
        extra_ids = list(g.get("extra_node_ids", []))
        extra_edges = g.get("extra_edges", [])

        # --- V10: применить override параметров sub-ассета ---
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

        # --- Main контур ---
        if len(contour) >= 2:
            x0, y0 = contour[0]
            main.moveTo(float(x0), float(y0))
            for pt in contour[1:]:
                main.lineTo(float(pt[0]), float(pt[1]))
            if g.get("closed", True):
                main.closeSubpath()

        # --- Карта node_id → (x, y) ---
        pos_map: dict[str, tuple[float, float]] = {}
        for i, nid in enumerate(node_ids):
            if i < len(contour):
                x, y = contour[i]
                pos_map[nid] = (float(x), float(y))
        for i, nid in enumerate(extra_ids):
            if i < len(extra_pts):
                x, y = extra_pts[i]
                pos_map[nid] = (float(x), float(y))

        # --- Extra edges ---
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
                sub_main, sub_extra, _ = self._collect_asset_paths(
                    sub, depth + 1,
                    param_overrides=comp.param_overrides,
                )

                t = QTransform()
                t.translate(comp.x, comp.y)
                t.rotate(-comp.rotation)
                t.scale(comp.scale, comp.scale)

                if not sub_main.isEmpty():
                    main.addPath(t.map(sub_main))
                if not sub_extra.isEmpty():
                    extra.addPath(t.map(sub_extra))

        # --- Центрируем по БАЗОВОМУ bbox (до override) ---
        # Фикс: центр не должен сдвигаться при растяжении.
        # Иначе низ детали (привязанный к родителю) уезжает —
        # и вся цепочка внизу едет за ним.
        if orig_contour:
            xs = [float(p[0]) for p in orig_contour]
            ys = [float(p[1]) for p in orig_contour]
            cx = (min(xs) + max(xs)) / 2
            cy = (min(ys) + max(ys)) / 2
            from PySide6.QtGui import QTransform
            shift = QTransform()
            shift.translate(-cx, -cy)
            main = shift.map(main)
            extra = shift.map(extra)
            return main, extra, (cx, cy)

        return main, extra, (0.0, 0.0)

    # ------------------------------------------------------------

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

        # Заливка белым, если включено — перекрывает линии за собой
        filled = bool(getattr(self._component, "filled", False))
        if filled:
            painter.setBrush(QBrush(QColor("#FFFFFF")))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)

        if not self._path.isEmpty():
            painter.drawPath(self._path)
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
        self.setZValue(100.0 + float(getattr(c, "layer", 0)))
        self.update()
        self.moved.emit()

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

            # Группа с именем == tag содержит узлы этого anchor'а
            group = None
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

    def _try_snap(self) -> None:
        """Найти ближайший совместимый anchor и прилипнуть."""
        scene = self.scene()
        if scene is None:
            return

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

            for my_tag, (mx, my) in my_world.items():
                for their_tag, (tx, ty) in their_world.items():
                    if (my_tag, their_tag) not in SNAP_PAIRS:
                        continue
                    dx = tx - mx
                    dy = ty - my
                    dist = (dx * dx + dy * dy) ** 0.5
                    if dist <= threshold_m:
                        if best is None or dist < best[0]:
                            best = (dist, my_tag, other, their_tag,
                                    dx, dy)

        if best is None:
            self.clear_snap_highlight()
            return

        _, my_tag, other, their_tag, dx, dy = best

        # Сначала очищаем старую пару
        self.clear_snap_highlight()

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
        self.clear_snap_highlight()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.prepareGeometryChange()
            self.update()
            # QTimer — чтобы избежать проблем с setParent во время сигнала
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, self._rebuild_handles)
        return super().itemChange(change, value)
