"""
ArchElement — базовый архитектурный элемент.

Чистые данные. Без Qt.

preset_id — необязательная ссылка на пресет, из которого создан
элемент. Используется только для истории создания, не влияет
на поведение. Все параметры instance хранит сам.
"""

from __future__ import annotations

import uuid
from typing import ClassVar


class ArchElement:
    """Базовый элемент архитектуры."""

    type: ClassVar[str] = "?"

    def __init__(
        self,
        id: str | None = None,
        floor: int = 1,
        notes: str = "",
        preset_id: str | None = None,
    ):
        self.id = id or self._generate_id()
        self.floor = floor
        self.notes = notes
        self.preset_id = preset_id

    # --- helpers ---

    @staticmethod
    def _generate_id() -> str:
        return uuid.uuid4().hex[:12]

    # --- сериализация ---

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "type": self.type,
            "floor": self.floor,
            "notes": self.notes,
        }
        if self.preset_id:
            d["preset_id"] = self.preset_id
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ArchElement":
        return cls(
            id=d["id"],
            floor=d.get("floor", 1),
            notes=d.get("notes", ""),
            preset_id=d.get("preset_id"),
        )

    def copy(self) -> "ArchElement":
        return type(self).from_dict(self.to_dict())
