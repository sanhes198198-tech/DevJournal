"""
RoomItem — QGraphicsObject для Room.

Item origin = (room.x, -room.y) в scene.
boundingRect = (0, -depth, width, depth).

Move: Qt двигает item при drag (ItemIsMovable).
Модель обновляется только на mouseRelease — через сигнал
move_finished → Editor → MoveRoomCommand.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Signal
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject

from ...model.room import Room
from ...render.plan_renderer import PlanRenderer
from ..coords import model_pos_to_scene, scene_pos_to_model


# Шаг округления при move (метры)
MOVE_ROUND_STEP = 0.1


class RoomItem(QGraphicsObject):
    """QGraphicsObject-обёртка для Room."""

    # id, old_x, old_y, new_x, new_y
    move_finished = Signal(str, float, float, float, float)

    def __init__(self, room: Room, parent=None):
        super().__init__(parent)

        self._room = room
        self._drag_old_pos: tuple[float, float] | None = None

        # Selectable
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
            True,
        )

        # Movable — теперь включено
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
            True,
        )

        # Geometry changes для snap (потом) и для перерисовки
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges,
            True,
        )

        self.setZValue(1.0)

        # Позиция
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
        return QRectF(
            0.0,
            -self._room.depth,
            self._room.width,
            self._room.depth,
        )

    def paint(self, painter, option, widget=None) -> None:
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
        """Перечитывает всё из модели."""
        self.prepareGeometryChange()

        sx, sy = model_pos_to_scene(self._room.x, self._room.y)
        self.setPos(sx, sy)

        self.update()

    # ============================================================
    # DRAG (Move)
    # ============================================================

    def mousePressEvent(self, event) -> None:
        # Запомнить начальную позицию из модели
        self._drag_old_pos = (self._room.x, self._room.y)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)

        if self._drag_old_pos is None:
            return

        old_x, old_y = self._drag_old_pos
        self._drag_old_pos = None

        # Текущая позиция в scene → model
        pos = self.pos()
        new_x, new_y = scene_pos_to_model(pos.x(), pos.y())

        # Округление
        new_x = round(new_x / MOVE_ROUND_STEP) * MOVE_ROUND_STEP
        new_y = round(new_y / MOVE_ROUND_STEP) * MOVE_ROUND_STEP

        # Округлить до 1 знака, чтобы 0.1+0.2 != 0.30000000004
        new_x = round(new_x, 1)
        new_y = round(new_y, 1)

        if (old_x, old_y) == (new_x, new_y):
            return

        self.move_finished.emit(
            self._room.id,
            old_x,
            old_y,
            new_x,
            new_y,
        )

    # ============================================================
    # СЕЛЕКЦИЯ
    # ============================================================

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update()
        return super().itemChange(change, value)
