"""
Asset — параметризованный архитектурный объект.

Надстройка над VectorContour: контур остаётся чистой геометрией,
а Asset добавляет метаданные (имя, тип, группы, параметры, правила).

V3: только создание, сериализация. Без UI параметров и генерации.
"""

from __future__ import annotations

import uuid
from typing import Any

from .contour import VectorContour


# ============================================================
# ТИПЫ ASSET (категории назначения)
# ============================================================

ASSET_TYPES: tuple[tuple[str, str], ...] = (
    ("tower_body", "Башня — тело"),
    ("tower_tier", "Башня — ярус"),
    ("roof", "Крыша"),
    ("dome", "Купол"),
    ("window", "Окно"),
    ("door", "Дверь"),
    ("wall_section", "Участок стены"),
    ("foundation", "Основание"),
    ("ornament", "Декор"),
    ("other", "Прочее"),
)

ASSET_TYPE_IDS: tuple[str, ...] = tuple(t[0] for t in ASSET_TYPES)


# ============================================================
# ASSET
# ============================================================

class Asset:
    """Параметризованный архитектурный ассет."""

    def __init__(
        self,
        asset_id: str | None = None,
        name: str = "Новый ассет",
        type_: str = "other",
        geometry: dict | None = None,
        parameters: dict | None = None,
        generation_rules: dict | None = None,
    ):
        self.id = asset_id or self._generate_id()
        self.name = name
        self.type = type_ if type_ in ASSET_TYPE_IDS else "other"
        self.geometry = geometry or self._empty_geometry()
        self.parameters = parameters or {}
        self.generation_rules = generation_rules or self._default_rules()

    # ------------------------------------------------------------
    # ФАБРИКИ
    # ------------------------------------------------------------

    @staticmethod
    def _generate_id() -> str:
        return uuid.uuid4().hex[:12]

    @staticmethod
    def _empty_geometry() -> dict:
        return {
            "contour": [],
            "closed": True,
            "units": "m",
            "node_ids": [],
            "groups": {},
        }

    @staticmethod
    def _default_rules() -> dict:
        return {
            "allow_width_variation": False,
            "allow_height_variation": False,
            "irregularity": 0.0,
            "repeatable": False,
        }

    @classmethod
    def from_contour(
        cls,
        contour: VectorContour,
        name: str = "Новый ассет",
        type_: str = "other",
        asset_id: str | None = None,
    ) -> "Asset":
        """Создать Asset из существующего VectorContour.

        Автоматически создаёт node_ids и технические группы рёбер.
        asset_id — если передан, сохраняется (для Save поверх).
        """
        points = list(contour.points)
        n = len(points)

        node_ids = [f"n_{i:03d}" for i in range(n)]

        groups: dict[str, list[str]] = {}
        if n >= 2:
            segments = range(n) if contour.closed else range(n - 1)
            for i in segments:
                a = node_ids[i]
                b = node_ids[(i + 1) % n]
                groups[f"edge_{i:03d}"] = [a, b]

        geometry = {
            "contour": [[float(x), float(y)] for (x, y) in points],
            "closed": bool(contour.closed),
            "units": "m",
            "node_ids": node_ids,
            "groups": groups,
        }

        return cls(
            asset_id=asset_id,
            name=name,
            type_=type_,
            geometry=geometry,
        )

    # ------------------------------------------------------------
    # СЕРИАЛИЗАЦИЯ
    # ------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "geometry": self.geometry,
            "parameters": self.parameters,
            "generation_rules": self.generation_rules,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Asset":
        return cls(
            asset_id=d.get("id"),
            name=d.get("name", "Новый ассет"),
            type_=d.get("type", "other"),
            geometry=d.get("geometry") or cls._empty_geometry(),
            parameters=d.get("parameters") or {},
            generation_rules=d.get("generation_rules") or cls._default_rules(),
        )

    # ------------------------------------------------------------
    # ДОСТУП
    # ------------------------------------------------------------

    def points(self) -> list[tuple[float, float]]:
        return [(float(p[0]), float(p[1])) for p in self.geometry.get("contour", [])]

    def is_closed(self) -> bool:
        return bool(self.geometry.get("closed", True))

    def node_count(self) -> int:
        return len(self.geometry.get("node_ids", []))

    def group_count(self) -> int:
        return len(self.geometry.get("groups", {}))
