"""
Registry — соответствие type_name → класс элемента.

Используется при загрузке JSON:
    element_from_dict(d)  →  Room(...) / Wall(...) / ...

При добавлении новых типов — расширить ELEMENT_TYPES.
"""

from __future__ import annotations

from .element import ArchElement
from .room import Room


ELEMENT_TYPES: dict[str, type[ArchElement]] = {
    "room": Room,
}


class UnknownElementType(Exception):
    """Неизвестный type в JSON."""
    pass


def element_from_dict(d: dict) -> ArchElement:
    """Создаёт элемент по словарю.

    Кидает UnknownElementType, если type не зарегистрирован
    или отсутствует.
    """
    t = d.get("type")
    if not t:
        raise UnknownElementType("Element missing 'type' field")

    cls = ELEMENT_TYPES.get(t)
    if cls is None:
        raise UnknownElementType(f"Unknown element type: {t!r}")

    return cls.from_dict(d)
