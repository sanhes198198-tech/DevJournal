"""
ComponentItem — QGraphicsObject для одного Component.

Рисует контур ссылочного Asset'а (main + extra_edges).
Позиция/поворот/масштаб — из Component.
Сцена Y↑ (см. ConstructorCanvas.scale(ppm, -ppm)) — здесь
координаты в model-метрах без флипа.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject


ASSET_LINE = QColor("#1A1A1A")
ASSET_LINE_SELECTED = QColor("#0055CC")
ORPHAN_COLOR = QColor("#CC3333")
LINE_WIDTH = 1.2
LINE_WIDTH_SELECTED = 2.0
ORPHAN_SIZE_M = 1.0


class ComponentItem(QGraphicsObject):
    """QGraphicsObject-обёртка для Component."""

    # Эмитится после завершения drag или после apply_from_component
    moved = Signal()

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
        """Позиция/поворот/масштаб из Component.

        Y↑ в сцене → rotation инвертируем.
        """
        c = self._component
        self.setPos(c.x, c.y)
        self.setRotation(-c.rotation)
        self.setScale(c.scale)

    # ------------------------------------------------------------

    def _rebuild_paths(self) -> None:
        self._path = QPainterPath()
        self._extra_path = QPainterPath()

        if self._asset is None:
            return

        # Рекурсивная сборка (центрирование уже сделано внутри)
        main, extra = self._collect_asset_paths(
            self._asset, depth=0,
        )
        self._path = main
        self._extra_path = extra
        self._offset_x = 0.0
        self._offset_y = 0.0

    def _collect_asset_paths(
        self, asset, depth: int,
    ) -> tuple[QPainterPath, QPainterPath]:
        """Собрать main + extra из asset'а рекурсивно.

        Возвращает (main_path, extra_path).
        """
        main = QPainterPath()
        extra = QPainterPath()

        if asset is None:
            return main, extra

        if depth > self.MAX_DEPTH:
            return main, extra

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
                sub_main, sub_extra = self._collect_asset_paths(
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

        # --- Центрируем каждый asset до применения (общий bbox) ---
        r = QRectF()
        if not main.isEmpty():
            r = main.boundingRect()
        if not extra.isEmpty():
            er = extra.boundingRect()
            r = r.united(er) if not r.isEmpty() else er

        if not r.isEmpty():
            from PySide6.QtGui import QTransform
            shift = QTransform()
            shift.translate(-r.center().x(), -r.center().y())
            main = shift.map(main)
            extra = shift.map(extra)

        return main, extra

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
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if not self._path.isEmpty():
            painter.drawPath(self._path)
        if not self._extra_path.isEmpty():
            painter.drawPath(self._extra_path)

    # ------------------------------------------------------------

    def apply_from_component(self) -> None:
        """Пересобрать transform из компонента (после правки в панели)."""
        c = self._component
        self.setPos(c.x, c.y)
        self.setRotation(-c.rotation)
        self.setScale(c.scale)
        self.update()
        self.moved.emit()

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

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update()
        return super().itemChange(change, value)
