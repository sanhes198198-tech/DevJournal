"""
ArchitectureModel — корневая модель архитектурного документа.

Без Qt. Чистые данные.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


SCHEMA_VERSION = 1


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class ArchitectureModel:
    """Корневая модель архитектуры.

    В M0 — контейнер. elements пустой, наполнится в M1+.
    """

    def __init__(
        self,
        meta: dict | None = None,
        building: dict | None = None,
        elements: dict | None = None,
        helpers: dict | None = None,
        schema_version: int = SCHEMA_VERSION,
    ):
        self.schema_version = schema_version
        self.meta = meta or self._default_meta()
        self.building = building or self._default_building()
        self.elements = elements or {}
        self.helpers = helpers or {"humans": [], "measures": []}

    # --- дефолты ---

    @staticmethod
    def _default_meta() -> dict:
        now = _now_iso()
        return {
            "name": "Архитектура",
            "units": "m",
            "created": now,
            "modified": now,
            "notes": "",
        }

    @staticmethod
    def _default_building() -> dict:
        return {
            "id": "main",
            "name": "Main",
            "defaults": {},
        }

    # --- фабрики ---

    @classmethod
    def create_empty(cls, name: str = "Архитектура") -> "ArchitectureModel":
        model = cls()
        model.meta["name"] = name
        return model

    @classmethod
    def from_dict(cls, d: dict) -> "ArchitectureModel":
        return cls(
            schema_version=d.get("schema_version", SCHEMA_VERSION),
            meta=d.get("meta") or cls._default_meta(),
            building=d.get("building") or cls._default_building(),
            elements=d.get("elements") or {},
            helpers=d.get("helpers") or {"humans": [], "measures": []},
        )

    # --- сериализация ---

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "meta": self.meta,
            "building": self.building,
            "elements": self.elements,
            "helpers": self.helpers,
        }

    def touch_modified(self) -> None:
        self.meta["modified"] = _now_iso()
