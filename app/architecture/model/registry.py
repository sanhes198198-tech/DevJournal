"""
Registry — соответствие type_name → класс элемента.
"""

from __future__ import annotations

from .element import ArchElement
from .room import Room
from .asset_instance import AssetInstance


ELEMENT_TYPES: dict[str, type[ArchElement]] = {
    "room": Room,
    "asset_instance": AssetInstance,
}


class UnknownElementType(Exception):
    """Неизвестный type в JSON."""
    pass


def element_from_dict(d: dict) -> ArchElement:
    """Создаёт элемент по словарю."""
    t = d.get("type")
    if not t:
        raise UnknownElementType("Element missing 'type' field")

    cls = ELEMENT_TYPES.get(t)
    if cls is None:
        raise UnknownElementType(f"Unknown element type: {t!r}")

    return cls.from_dict(d)
