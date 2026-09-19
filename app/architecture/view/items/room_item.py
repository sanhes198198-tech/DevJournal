"""
RoomItem — QGraphicsObject для Room.

Item origin = (room.x, -room.y) в scene.
boundingRect = (0, -depth, width, depth).
"""

from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject

from ...model.room import Room
from ...render.plan_renderer import PlanRenderer
from ..coords import model_pos_to_scene


class RoomItem(QGraphicsObject):
    """QGraphicsObject-обёртка для Room."""

    def __init__(self, room: Room, parent=None):
        super().__init__(parent)

        self._room = room

        # Selectable + flag для itemChange
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
            True,
        )
        # ItemIsMovable = False в M1b.
        # Включим в M1d вместе с MoveRoomCommand.

        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges,
            True,
        )

        self.setZValue(1.0)

        # Позиция в scene
        sx, sy = model_pos_to_scene(room.x, room.y)
        self.setPos(sx, sy)

    # ============================================================
    # ДОСТУП
    # ============================================================

    @property
    def room(self) -> Room:
        return self._room

    @property
    def room_id(self) -> str:
        return self._room.id

    # ============================================================
    # ГЕОМЕТРИЯ
    # ============================================================

    def boundingRect(self) -> QRectF:
        """Item origin = (room.x, -room.y).

        Комната растёт на север (Model Y+) = в scene на -Y.
        Значит rect: (0, -depth, width, depth).
        """
        return QRectF(
            0.0,
            -self._room.depth,
            self._room.width,
            self._room.depth,
        )

    def paint(self, painter, option, widget=None) -> None:
        # Текущий zoom — из painter
        ppm = abs(painter.transform().m11()) or 50.0

        PlanRenderer.draw_room(
            painter,
            self.boundingRect(),
            self._room,
            selected=self.isSelected(),
            ppm=ppm,
        )

    # ============================================================
    # СИНХРОНИЗАЦИЯ С МОДЕЛЬЮ
    # ============================================================

    def sync_from_model(self) -> None:
        """Перечитывает всё из модели и перерисовывается.

        Вызывается сценой при element_changed.
        """
        self.prepareGeometryChange()

        sx, sy = model_pos_to_scene(self._room.x, self._room.y)
        self.setPos(sx, sy)

        self.update()

    # ============================================================
    # СЕЛЕКЦИЯ
    # ============================================================

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update()
        return super().itemChange(change, value)
