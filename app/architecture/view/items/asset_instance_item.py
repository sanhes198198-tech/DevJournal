"""
AssetInstanceItem — QGraphicsObject для AssetInstance.

Геометрия из Asset.geometry.contour в ЛОКАЛЬНЫХ координатах.
Transform (scale + rotation) применяется через QTransform на item.
Позиция (x, y) — через setPos.

Qt сам заботится о hit-test, boundingRect и отрисовке с учётом transform.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor, QPainterPath, QPen, QTransform,
)
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject

from ...model.asset_instance import AssetInstance
from ..coords import model_pos_to_scene, scene_pos_to_model


MOVE_ROUND_STEP = 0.1

ORPHAN_SIZE_M = 1.0
ORPHAN_COLOR = QColor("#CC3333")

ASSET_LINE = QColor("#1A1A1A")
ASSET_LINE_SELECTED = QColor("#0055CC")
LINE_WIDTH = 1.2
LINE_WIDTH_SELECTED = 2.0


class AssetInstanceItem(QGraphicsObject):
    """QGraphicsObject-обёртка для AssetInstance."""

    move_finished = Signal(str, float, float, float, float)

    def __init__(self, instance: AssetInstance, asset=None, parent=None):
        super().__init__(parent)

        self._instance = instance
        self._asset = asset
        self._drag_old_pos: tuple[float, float] | None = None

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges,
            True,
        )

        self.setZValue(3.0)

        self._apply_transform()

    # ------------------------------------------------------------

    @property
    def instance(self) -> AssetInstance:
        return self._instance

    @property
    def instance_id(self) -> str:
        return self._instance.id

    @property
    def element(self):
        return self._instance

    @property
    def element_id(self) -> str:
        return self._instance.id

    @property
    def is_orphan(self) -> bool:
        return self._asset is None

    def set_asset(self, asset) -> None:
        self._asset = asset
        self.prepareGeometryChange()
        self.update()

    # ------------------------------------------------------------
    # TRANSFORM (через Qt)
    # ------------------------------------------------------------

    def _apply_transform(self) -> None:
        """Устанавливает QTransform: scale + rotation.

        Позиция — отдельно через setPos.
        """
        t = QTransform()
        t.scale(self._instance.scale, self._instance.scale)
        t.rotate(-self._instance.rotation)
        self.setTransform(t)

        sx, sy = model_pos_to_scene(
            self._instance.x, self._instance.y
        )
        self.setPos(sx, sy)

    # ------------------------------------------------------------
    # ГЕОМЕТРИЯ (в ЛОКАЛЬНЫХ координатах, без transform)
    # ------------------------------------------------------------

    def _base_path(self) -> QPainterPath:
        path = QPainterPath()
        if self._asset is None:
            return path

        contour = self._asset.geometry.get("contour", [])
        if len(contour) < 2:
            return path

        x0, y0 = contour[0]
        path.moveTo(x0, -y0)

        for pt in contour[1:]:
            x, y = pt
            path.lineTo(x, -y)

        if self._asset.geometry.get("closed", True):
            path.closeSubpath()

        return path

    def _extra_path(self) -> QPainterPath:
        """Дополнительные линии: extra_edges между узлами
        (main + extra), плюс изолированные extra_points."""
        path = QPainterPath()
        if self._asset is None:
            return path

        g = self._asset.geometry
        node_ids = list(g.get("node_ids", []))
        contour = list(g.get("contour", []))
        extra_pts = list(g.get("extra_points", []))
        extra_ids = list(g.get("extra_node_ids", []))
        edges = list(g.get("extra_edges", []))

        # Карта: node_id → (x, y)
        pos_map: dict[str, tuple[float, float]] = {}
        for i, nid in enumerate(node_ids):
            if i < len(contour):
                x, y = contour[i]
                pos_map[nid] = (float(x), float(y))
        for i, nid in enumerate(extra_ids):
            if i < len(extra_pts):
                x, y = extra_pts[i]
                pos_map[nid] = (float(x), float(y))

        # Линии
        for edge in edges:
            if not isinstance(edge, (list, tuple)) or len(edge) != 2:
                continue
            a_id, b_id = edge
            pa = pos_map.get(a_id)
            pb = pos_map.get(b_id)
            if pa is None or pb is None:
                continue
            path.moveTo(pa[0], -pa[1])
            path.lineTo(pb[0], -pb[1])

        return path

    def _orphan_rect(self) -> QRectF:
        return QRectF(
            0.0, -ORPHAN_SIZE_M,
            ORPHAN_SIZE_M, ORPHAN_SIZE_M,
        )

    def boundingRect(self) -> QRectF:
        if self._asset is None:
            return self._orphan_rect().adjusted(-0.1, -0.1, 0.1, 0.1)

        path = self._base_path()
        extra = self._extra_path()
        if path.isEmpty() and extra.isEmpty():
            return QRectF()

        r = path.boundingRect()
        if not extra.isEmpty():
            r = r.united(extra.boundingRect())
        return r.adjusted(-0.3, -0.3, 0.3, 0.3)

    def shape(self) -> QPainterPath:
        if self._asset is None:
            p = QPainterPath()
            p.addRect(self._orphan_rect())
            return p

        from PySide6.QtGui import QPainterPathStroker
        path = self._base_path()
        extra = self._extra_path()

        combined = QPainterPath(path)
        if not extra.isEmpty():
            combined.addPath(extra)

        if combined.isEmpty():
            return combined

        stroker = QPainterPathStroker()
        stroker.setWidth(0.5)
        return stroker.createStroke(combined)

    def paint(self, painter, option, widget=None) -> None:
        painter.setRenderHint(painter.RenderHint.Antialiasing, True)

        if self._asset is None:
            pen = QPen(ORPHAN_COLOR, 1.5)
            pen.setCosmetic(True)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            r = self._orphan_rect()
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

        path = self._base_path()
        if path.isEmpty():
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
        painter.drawPath(path)

    # ------------------------------------------------------------
    # СИНХРОНИЗАЦИЯ
    # ------------------------------------------------------------

    def sync_from_model(self) -> None:
        """Обновить transform и позицию из модели.

        Вызывается при element_changed (после ModifyElementCommand).
        """
        self.prepareGeometryChange()
        self._apply_transform()
        self.update()

    # ------------------------------------------------------------
    # MOVE
    # ------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        self._drag_old_pos = (self._instance.x, self._instance.y)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)

        if self._drag_old_pos is None:
            return

        old_x, old_y = self._drag_old_pos
        self._drag_old_pos = None

        pos = self.pos()
        new_x, new_y = scene_pos_to_model(pos.x(), pos.y())

        new_x = round(new_x / MOVE_ROUND_STEP) * MOVE_ROUND_STEP
        new_y = round(new_y / MOVE_ROUND_STEP) * MOVE_ROUND_STEP
        new_x = round(new_x, 1)
        new_y = round(new_y, 1)

        if (old_x, old_y) == (new_x, new_y):
            return

        self.move_finished.emit(
            self._instance.id, old_x, old_y, new_x, new_y,
        )

    # ------------------------------------------------------------

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update()
        return super().itemChange(change, value)
