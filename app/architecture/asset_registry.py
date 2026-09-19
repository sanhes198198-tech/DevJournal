"""
AssetRegistry — библиотека векторных Asset'ов для архитектуры.

Два источника:
  - глобальная:  app/vector_editor/assets/
  - проектная:   boards/<project>/assets/

Проектная перезаписывает глобальную, если asset_id совпал.

Использование:
    reg = AssetRegistry(project_folder=Path("boards/TEST4"))
    reg.load_all()
    asset = reg.get("tower_body_01")
"""

from __future__ import annotations

import sys
from pathlib import Path

# Импорт Asset из vector_editor (не поднимаем весь редактор)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "vector_editor"))


def _load_asset_from_file(path: Path):
    """Загружает Asset из JSON. Возвращает None при ошибке."""
    from app.vector_editor.io import load_asset, StorageError
    try:
        return load_asset(path)
    except StorageError as e:
        print(f"[AssetRegistry] skip {path.name}: {e}")
        return None


class AssetRegistry:
    """Реестр Asset'ов — глобальные + проектные."""

    # Папка глобальной библиотеки (из vector_editor)
    GLOBAL_DIR = Path(__file__).resolve().parent.parent / "vector_editor" / "assets"

    def __init__(self, project_folder: Path | None = None):
        self._project_folder = Path(project_folder) if project_folder else None
        self._assets: dict[str, object] = {}   # asset_id → Asset

    # ------------------------------------------------------------

    def _project_assets_dir(self) -> Path | None:
        if self._project_folder is None:
            return None
        return self._project_folder / "assets"

    def load_all(self) -> None:
        """Загружает все Asset'ы из двух папок."""
        self._assets.clear()

        # 1. Глобальные
        if self.GLOBAL_DIR.exists():
            for p in sorted(self.GLOBAL_DIR.glob("*.json")):
                asset = _load_asset_from_file(p)
                if asset is not None:
                    self._assets[asset.id] = asset

        # 2. Проектные (override)
        proj_dir = self._project_assets_dir()
        if proj_dir is not None and proj_dir.exists():
            for p in sorted(proj_dir.glob("*.json")):
                asset = _load_asset_from_file(p)
                if asset is not None:
                    self._assets[asset.id] = asset

    # ------------------------------------------------------------

    def get(self, asset_id: str):
        return self._assets.get(asset_id)

    def all(self) -> list:
        return list(self._assets.values())

    def by_type(self, type_: str) -> list:
        items = [a for a in self._assets.values() if a.type == type_]
        return sorted(items, key=lambda a: (a.name or a.id).lower())

    def count(self) -> int:
        return len(self._assets)

    def has(self, asset_id: str) -> bool:
        return asset_id in self._assets
