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

    def _rebuild_paths(self) -> None:
        self._path = QPainterPath()
        self._extra_path = QPainterPath()

        if self._asset is None:
            return

        # Рекурсивная сборка (центрирование внутри)
        main, extra, center = self._collect_asset_paths(
            self._asset, depth=0,
        )
        self._path = main
        self._extra_path = extra
        # Запоминаем центр bbox — он же используется для anchor'ов
        self._center_x, self._center_y = center

    def _collect_asset_paths(
        self, asset, depth: int,
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
        contour = g.get("contour", [])
        node_ids = g.get("node_ids", [])
        extra_pts = g.get("extra_points", [])
        extra_ids = g.get("extra_node_ids", [])
        extra_edges = g.get("extra_edges", [])

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
                )

                t = QTransform()
                t.translate(comp.x, comp.y)
                t.rotate(-comp.rotation)
                t.scale(comp.scale, comp.scale)

                if not sub_main.isEmpty():
                    main.addPath(t.map(sub_main))
                if not sub_extra.isEmpty():
                    extra.addPath(t.map(sub_extra))

        # --- Центрируем по общему bbox и возвращаем центр ---
        r = QRectF()
        if not main.isEmpty():
            r = main.boundingRect()
        if not extra.isEmpty():
            er = extra.boundingRect()
            r = r.united(er) if not r.isEmpty() else er

        if not r.isEmpty():
            from PySide6.QtGui import QTransform
            cx = r.center().x()
            cy = r.center().y()
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
        return r.adjusted(-0.3, -0.3, 0.3, 0.3)

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
        """Anchor'ы ссылочного asset'а в ЛОКАЛЬНЫХ координатах item."""
        if self._asset is None:
            print("[ANCHORS-LOCAL] asset is None")
            return {}
        raw = self._asset.anchors()
        # anchor'ы в asset.anchors() в сырых координатах.
        # Контур уже отцентрирован → вычитаем тот же центр.
        return {
            tag: (x - self._center_x, y - self._center_y)
            for tag, (x, y) in raw.items()
        }

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

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)
        self._try_snap()

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)

        # Снапим к сетке 0.1 м
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

        # Убираем подсветку snap
        self.clear_snap_highlight()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update()
        return super().itemChange(change, value)
