"""
ArchitectureModel — корневая модель архитектурного документа.

Без Qt. Чистые данные.

elements — dict[str, ArchElement].
Сериализация в JSON: тот же dict (id → dict).
"""

from __future__ import annotations

from datetime import datetime

from .element import ArchElement
from .registry import element_from_dict, UnknownElementType


SCHEMA_VERSION = 1


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class ArchitectureModel:
    """Корневая модель архитектуры."""

    def __init__(
        self,
        meta: dict | None = None,
        building: dict | None = None,
        elements: dict[str, ArchElement] | None = None,
        helpers: dict | None = None,
        schema_version: int = SCHEMA_VERSION,
    ):
        self.schema_version = schema_version
        self.meta = meta or self._default_meta()
        self.building = building or self._default_building()
        self.elements: dict[str, ArchElement] = elements or {}
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
        elements_raw = d.get("elements") or {}
        elements: dict[str, ArchElement] = {}

        if isinstance(elements_raw, dict):
            for el_id, el_dict in elements_raw.items():
                # Падаем при неизвестном типе — не теряем данные.
                el = element_from_dict(el_dict)
                elements[el_id] = el

        return cls(
            schema_version=d.get("schema_version", SCHEMA_VERSION),
            meta=d.get("meta") or cls._default_meta(),
            building=d.get("building") or cls._default_building(),
            elements=elements,
            helpers=d.get("helpers") or {"humans": [], "measures": []},
        )

    # --- элементы ---

    def add_element(self, el: ArchElement) -> None:
        if el.id in self.elements:
            raise ValueError(f"Element {el.id!r} already exists")
        self.elements[el.id] = el

    def remove_element(self, element_id: str) -> ArchElement | None:
        return self.elements.pop(element_id, None)

    def get_element(self, element_id: str) -> ArchElement | None:
        return self.elements.get(element_id)

    def has_element(self, element_id: str) -> bool:
        return element_id in self.elements

    # --- сериализация ---

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "meta": self.meta,
            "building": self.building,
            "elements": {
                el_id: el.to_dict()
                for el_id, el in self.elements.items()
            },
            "helpers": self.helpers,
        }

    def touch_modified(self) -> None:
        self.meta["modified"] = _now_iso()
