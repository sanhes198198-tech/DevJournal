"""
QUndoCommand-классы для Constructor.

Каждая команда умеет apply() и revert(), знает как обновить UI.
Merge — для объединения подряд идущих изменений одного параметра
(например, при перетаскивании ручки ползунка).
"""
from __future__ import annotations

from PySide6.QtGui import QUndoCommand


class SetParamOverrideCommand(QUndoCommand):
    """Изменение override параметра у компонента."""

    def __init__(
        self,
        comp,
        name: str,
        old_value,
        new_value: float,
        on_apply,
    ):
        super().__init__(f"Изменить {name}")
        self._comp = comp
        self._name = name
        self._old = old_value
        self._new = float(new_value)
        self._on_apply = on_apply

    def id(self) -> int:
        return 1001

    def redo(self) -> None:
        self._comp.set_param_override(self._name, self._new)
        self._on_apply()

    def undo(self) -> None:
        if self._old is None:
            self._comp.param_overrides.pop(self._name, None)
        else:
            self._comp.set_param_override(self._name, self._old)
        self._on_apply()

    def mergeWith(self, other) -> bool:
        if not isinstance(other, SetParamOverrideCommand):
            return False
        if self._comp.id != other._comp.id:
            return False
        if self._name != other._name:
            return False
        self._new = other._new
        return True

class MoveComponentCommand(QUndoCommand):
    """Перемещение компонента (сдвиг мышью)."""

    def __init__(
        self,
        comp,
        old_x: float,
        old_y: float,
        new_x: float,
        new_y: float,
        on_apply,
    ):
        super().__init__("Переместить компонент")
        self._comp = comp
        self._old = (float(old_x), float(old_y))
        self._new = (float(new_x), float(new_y))
        self._on_apply = on_apply

    def id(self) -> int:
        return 1002

    def redo(self) -> None:
        self._comp.x = self._new[0]
        self._comp.y = self._new[1]
        self._on_apply()

    def undo(self) -> None:
        self._comp.x = self._old[0]
        self._comp.y = self._old[1]
        self._on_apply()

    def mergeWith(self, other) -> bool:
        if not isinstance(other, MoveComponentCommand):
            return False
        if self._comp.id != other._comp.id:
            return False
        self._new = other._new
        return True
