"""
ArchElement — базовый архитектурный элемент.

Чистые данные. Без Qt.
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
    ):
        self.id = id or self._generate_id()
        self.floor = floor
        self.notes = notes

    # --- helpers ---

    @staticmethod
    def _generate_id() -> str:
        return uuid.uuid4().hex[:12]

    # --- сериализация ---

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "floor": self.floor,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ArchElement":
        """Базовая реализация.

        Наследники переопределяют и вызывают свои поля.
        """
        return cls(
            id=d["id"],
            floor=d.get("floor", 1),
            notes=d.get("notes", ""),
        )

    def copy(self) -> "ArchElement":
        """Независимая копия. Для undo/redo."""
        return type(self).from_dict(self.to_dict())
