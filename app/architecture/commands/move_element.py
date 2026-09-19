"""
MoveRoomCommand — изменение позиции комнаты.

При drag Qt сам двигает RoomItem через setPos().
Модель обновляется ТОЛЬКО на mouseRelease — через эту команду.
"""

from __future__ import annotations

from PySide6.QtGui import QUndoCommand


class MoveRoomCommand(QUndoCommand):
    """Команда: переместить комнату."""

    def __init__(
        self,
        document,
        element_id: str,
        old_x: float,
        old_y: float,
        new_x: float,
        new_y: float,
        parent=None,
    ):
        super().__init__("Переместить комнату", parent)
        self._document = document
        self._element_id = element_id
        self._old_x = old_x
        self._old_y = old_y
        self._new_x = new_x
        self._new_y = new_y

    def redo(self) -> None:
        self._document.update_element(
            self._element_id,
            x=self._new_x,
            y=self._new_y,
        )

    def undo(self) -> None:
        self._document.update_element(
            self._element_id,
            x=self._old_x,
            y=self._old_y,
        )
