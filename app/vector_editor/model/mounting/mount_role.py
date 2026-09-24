"""
MountRole - фиксированные роли точек крепления.

Что можно поставить в эту точку.
None допустим для legacy-ассетов после миграции
(система не угадывает роль автоматически).
"""

from __future__ import annotations

from enum import StrEnum


class MountRole(StrEnum):
    """Роль точки крепления."""
    WINDOW = "window"
    DOOR = "door"
    FOUNDATION = "foundation"
    CORNICE = "cornice"
    DECOR = "decor"


def parse_role(value) -> MountRole | None:
    """Разобрать роль из строки. None для пустых/невалидных."""
    if value is None or value == "":
        return None
    if isinstance(value, MountRole):
        return value
    try:
        return MountRole(str(value))
    except (ValueError, TypeError):
        return None


def role_to_str(role) -> str | None:
    """Сериализовать роль в строку."""
    if role is None:
        return None
    if isinstance(role, MountRole):
        return role.value
    return str(role)