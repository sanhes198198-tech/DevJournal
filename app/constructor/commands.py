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
