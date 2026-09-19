"""
PresetRegistry — загрузка пресетов из JSON.

Пресеты — глобальная библиотека DevJournal, не связана с проектом.
Проект хранит только preset_id в созданных instance.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Preset:
    """Один пресет — шаблон для создания элемента."""
    id: str
    type: str
    name: str
    category: str
    defaults: dict = field(default_factory=dict)


class PresetRegistry:
    """Загружает и хранит все пресеты."""

    def __init__(self, data_dir: Path | None = None):
        self._presets: dict[str, Preset] = {}
        self._data_dir = data_dir or self._default_data_dir()

    @staticmethod
    def _default_data_dir() -> Path:
        return Path(__file__).parent / "data"

    # ------------------------------------------------------------

    def load_all(self) -> None:
        """Загружает все .json рекурсивно из data_dir."""
        self._presets.clear()

        if not self._data_dir.exists():
            print(f"[presets] data dir not found: {self._data_dir}")
            return

        for json_file in self._data_dir.rglob("*.json"):
            self._load_file(json_file)

    def _load_file(self, path: Path) -> None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"[presets] skip {path.name}: {e}")
            return

        if not isinstance(data, dict):
            print(f"[presets] skip {path.name}: not a dict")
            return

        preset_id = data.get("id")
        if not preset_id:
            print(f"[presets] skip {path.name}: missing id")
            return

        preset = Preset(
            id=preset_id,
            type=data.get("type", "?"),
            name=data.get("name", preset_id),
            category=data.get("category", "default"),
            defaults=data.get("defaults", {}) or {},
        )
        self._presets[preset_id] = preset

    # ------------------------------------------------------------

    def get(self, preset_id: str) -> Preset | None:
        return self._presets.get(preset_id)

    def by_category(self, category: str) -> list[Preset]:
        items = [
            p for p in self._presets.values()
            if p.category == category
        ]
        return sorted(items, key=lambda p: p.name)

    def all(self) -> list[Preset]:
        return list(self._presets.values())

    def count(self) -> int:
        return len(self._presets)


# ============================================================
# SINGLETON
# ============================================================

_default_registry: PresetRegistry | None = None


def get_registry() -> PresetRegistry:
    """Ленивая инициализация глобального registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = PresetRegistry()
        _default_registry.load_all()
    return _default_registry
