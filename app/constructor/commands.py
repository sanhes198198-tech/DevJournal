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

class AddComponentCommand(QUndoCommand):
    """Добавление компонента в композит."""

    def __init__(
        self,
        composite,
        comp,
        on_create_item,
        on_remove_item,
    ):
        super().__init__("Добавить компонент")
        self._composite = composite
        self._comp = comp
        self._on_create_item = on_create_item
        self._on_remove_item = on_remove_item

    def redo(self) -> None:
        self._composite.add_component(self._comp)
        self._on_create_item(self._comp)

    def undo(self) -> None:
        self._on_remove_item(self._comp.id)
        self._composite.remove_component(self._comp.id)


class DeleteComponentCommand(QUndoCommand):
    """Удаление компонента из композита."""

    def __init__(
        self,
        composite,
        comp,
        on_create_item,
        on_remove_item,
    ):
        super().__init__("Удалить компонент")
        self._composite = composite
        self._comp = comp
        self._on_create_item = on_create_item
        self._on_remove_item = on_remove_item

    def redo(self) -> None:
        self._on_remove_item(self._comp.id)
        self._composite.remove_component(self._comp.id)

    def undo(self) -> None:
        self._composite.add_component(self._comp)
        self._on_create_item(self._comp)

class SetPropertyCommand(QUndoCommand):
    """Универсальная команда для скалярных полей Component.

    Используется для x/y/rotation/scale/layer — когда значение
    меняется из панели свойств (спинбоксы).

    mergeWith объединяет подряд идущие изменения одного поля,
    чтобы Ctrl+Z откатывал всю серию за один раз.
    """

    def __init__(
        self,
        target,
        field: str,
        old_value,
        new_value,
        on_apply,
    ):
        super().__init__(f"Изменить {field}")
        self._target = target
        self._field = field
        self._old = old_value
        self._new = new_value
        self._on_apply = on_apply

    def redo(self) -> None:
        setattr(self._target, self._field, self._new)
        self._on_apply()

    def undo(self) -> None:
        setattr(self._target, self._field, self._old)
        self._on_apply()

    # mergeWith НЕ реализуем — каждая команда отдельная,
    # чтобы Ctrl+Z откатывал по одному шагу.


class MoveWithReflowCommand(QUndoCommand):
    """Перемещение компонента + reflow детей одной командой.

    Откатывает ВСЕ затронутые компоненты за один Ctrl+Z.
    positions = {comp_id: (x, y)}
    """

    def __init__(
        self,
        before: dict,
        after: dict,
        items_by_comp_id: dict,
        composite,
    ):
        super().__init__("Переместить компонент")
        self._before = dict(before)
        self._after = dict(after)
        self._items = items_by_comp_id
        self._composite = composite

    def id(self) -> int:
        return 1003

    def _apply(self, positions: dict) -> None:
        for cid, (x, y) in positions.items():
            comp = self._composite.get_component(cid)
            if comp is None:
                continue
            comp.x = float(x)
            comp.y = float(y)
            item = self._items.get(cid)
            if item is not None:
                item.setPos(float(x), float(y))
                item.update()

    def redo(self) -> None:
        self._apply(self._after)

    def undo(self) -> None:
        self._apply(self._before)

    def mergeWith(self, other) -> bool:
        return False

