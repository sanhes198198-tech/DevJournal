"""
AssetInstance — экземпляр векторного Asset в сцене архитектуры.

Ссылается на Asset по asset_id. Сама геометрия не хранится —
загружается из библиотеки при рендере (см. AssetRegistry, M2b).

Если Asset не найден — instance всё равно валиден (status="orphan"),
рисуется заглушкой, Properties показывает warning.

Transform:
    x, y      — позиция в модели (метры)
    rotation  — угол в градусах (0 = как в Asset)
    scale     — равномерный масштаб (default 1.0)
"""

from __future__ import annotations

from .element import ArchElement


class AssetInstance(ArchElement):
    """Экземпляр векторного Asset в сцене."""

    type = "asset_instance"

    def __init__(
        self,
        id: str | None = None,
        floor: int = 1,
        notes: str = "",
        preset_id: str | None = None,
        asset_id: str = "",
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        scale: float = 1.0,
    ):
        super().__init__(
            id=id,
            floor=floor,
            notes=notes,
            preset_id=preset_id,
        )

        self.asset_id = asset_id
        self.x = float(x)
        self.y = float(y)
        self.rotation = float(rotation)
        self.scale = float(scale)

    # --- сериализация ---

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "asset_id": self.asset_id,
            "x": self.x,
            "y": self.y,
            "rotation": self.rotation,
            "scale": self.scale,
        })
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "AssetInstance":
        return cls(
            id=d["id"],
            floor=d.get("floor", 1),
            notes=d.get("notes", ""),
            preset_id=d.get("preset_id"),
            asset_id=d.get("asset_id", ""),
            x=float(d.get("x", 0.0)),
            y=float(d.get("y", 0.0)),
            rotation=float(d.get("rotation", 0.0)),
            scale=float(d.get("scale", 1.0)),
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.asset_id:
            errors.append("asset_id is required")
        if self.scale <= 0:
            errors.append("scale must be > 0")
        return errors
