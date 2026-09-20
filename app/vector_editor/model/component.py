"""
Component — ссылка на другой Asset внутри составного Asset'а.

Пример: башня состоит из [стена, купол, окно_1, окно_2].
Каждый — Component: ссылка на asset_id + позиция/поворот/масштаб.

Модель чистая, без Qt.
"""

from __future__ import annotations

import uuid


class Component:
    """Один компонент составного Asset'а."""

    def __init__(
        self,
        id: str | None = None,
        asset_id: str = "",
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        scale: float = 1.0,
        name: str = "",
        layer: int = 0,
        filled: bool = False,
    ):
        self.id = id or self._generate_id()
        self.asset_id = asset_id
        self.x = float(x)
        self.y = float(y)
        self.rotation = float(rotation)
        self.scale = float(scale) if scale > 0 else 1.0
        self.name = name
        self.layer = int(layer)
        self.filled = bool(filled)

    @staticmethod
    def _generate_id() -> str:
        return "c_" + uuid.uuid4().hex[:8]

    # ------------------------------------------------------------

    def is_valid(self) -> bool:
        """Базовая валидация: есть ссылка на asset."""
        return bool(self.asset_id)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "x": self.x,
            "y": self.y,
            "rotation": self.rotation,
            "scale": self.scale,
            "name": self.name,
            "layer": self.layer,
            "filled": self.filled,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Component":
        return cls(
            id=d.get("id"),
            asset_id=str(d.get("asset_id", "")),
            x=float(d.get("x", 0.0)),
            y=float(d.get("y", 0.0)),
            rotation=float(d.get("rotation", 0.0)),
            scale=float(d.get("scale", 1.0)),
            name=str(d.get("name", "")),
            layer=int(d.get("layer", 0)),
            filled=bool(d.get("filled", False)),
        )
