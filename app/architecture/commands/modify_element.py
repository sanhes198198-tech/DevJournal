"""
ModifyElementCommand — изменение одного поля элемента.

Поддерживает merge: последовательные правки одного поля одного
и того же элемента сливаются в одну команду. Тогда Ctrl+Z
откатывает всё изменение целиком, а не по одному шагу спинбокса.
"""

from __future__ import annotations

from PySide6.QtGui import QUndoCommand


# Уникальный id для merge-группы
MODIFY_COMMAND_ID = 1001


class ModifyElementCommand(QUndoCommand):
    """Команда: изменить одно поле элемента."""

    def __init__(
        self,
        document,
        element_id: str,
        field: str,
        old_value,
        new_value,
        parent=None,
    ):
        super().__init__(f"Изменить {field}", parent)
        self._document = document
        self._element_id = element_id
        self._field = field
        self._old_value = old_value
        self._new_value = new_value

    # --- merge ---

    def id(self) -> int:
        return MODIFY_COMMAND_ID

    def mergeWith(self, other: QUndoCommand) -> bool:
        if not isinstance(other, ModifyElementCommand):
            return False
        if self._element_id != other._element_id:
            return False
        if self._field != other._field:
            return False

        # Слить: сохраняем СТАРОЕ значение своё, берём НОВОЕ из other
        self._new_value = other._new_value
        return True

    # --- apply ---

    def redo(self) -> None:
        self._document.update_element(
            self._element_id,
            **{self._field: self._new_value},
        )

    def undo(self) -> None:
        self._document.update_element(
            self._element_id,
            **{self._field: self._old_value},
        )
