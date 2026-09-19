"""
Room — комната/помещение.

Позиция (x, y) — нижний-левый угол в МОДЕЛЬНЫХ координатах (Y вверх).

Комната растёт:
    width  → вправо (+X)
    depth  → вверх  (+Y)
    height → вверх  (+Z), для будущих проекций

Модель не накладывает жёстких ограничений на размеры.
Проверка — через validate(). UI может накладывать строже.
"""

from __future__ import annotations

from .element import ArchElement


class Room(ArchElement):
    """Комната."""

    type = "room"

    def __init__(
        self,
        id: str | None = None,
        floor: int = 1,
        notes: str = "",
        name: str = "Комната",
        x: float = 0.0,
        y: float = 0.0,
        width: float = 5.0,
        depth: float = 5.0,
        height: float = 3.0,
    ):
        super().__init__(id=id, floor=floor, notes=notes)

        self.name = name
        self.x = float(x)
        self.y = float(y)
        self.width = float(width)
        self.depth = float(depth)
        self.height = float(height)

    # --- сериализация ---

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "depth": self.depth,
            "height": self.height,
        })
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Room":
        return cls(
            id=d["id"],
            floor=d.get("floor", 1),
            notes=d.get("notes", ""),
            name=d.get("name", "Комната"),
            x=float(d.get("x", 0.0)),
            y=float(d.get("y", 0.0)),
            width=float(d.get("width", 5.0)),
            depth=float(d.get("depth", 5.0)),
            height=float(d.get("height", 3.0)),
        )

    # --- валидация ---

    def validate(self) -> list[str]:
        """Список ошибок. Пустой = ОК.

        Модельные ограничения минимальны:
        положительная геометрия. UI может быть строже.
        """
        errors: list[str] = []
        if self.width <= 0:
            errors.append("width must be > 0")
        if self.depth <= 0:
            errors.append("depth must be > 0")
        if self.height <= 0:
            errors.append("height must be > 0")
        return errors
