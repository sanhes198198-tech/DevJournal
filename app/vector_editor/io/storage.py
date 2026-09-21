"""
Сохранение и загрузка Asset'ов в JSON.

Файлы: app/vector_editor/assets/<asset_id>.json
"""

from __future__ import annotations

import json
from pathlib import Path

from ..model.asset import Asset


# Папка для библиотеки Asset'ов (принадлежит редактору)
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


class StorageError(Exception):
    """Ошибка сохранения или загрузки Asset'а."""


# ============================================================
# DIR
# ============================================================

def ensure_assets_dir() -> Path:
    """Создать папку assets, если её нет. Вернуть путь."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    return ASSETS_DIR


# ============================================================
# SAVE / LOAD
# ============================================================

def save_asset(asset: Asset, folder: Path | None = None) -> Path:
    """Сохранить Asset в JSON. Атомарно через .tmp.

    Возвращает путь к файлу.
    """
    target_dir = Path(folder) if folder else ASSETS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    path = target_dir / f"{asset.id}.json"
    tmp = path.with_suffix(path.suffix + ".tmp")

    try:
        data = asset.to_dict()
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except OSError as e:
        raise StorageError(f"Не удалось записать Asset: {e}") from e

    return path


def load_asset(path: Path) -> Asset:
    """Загрузить Asset из JSON-файла."""
    path = Path(path)

    if not path.exists():
        raise StorageError(f"Файл не найден: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise StorageError(f"Некорректный JSON: {e}") from e
    except OSError as e:
        raise StorageError(f"Не удалось прочитать файл: {e}") from e

    if not isinstance(data, dict):
        raise StorageError("Ожидался объект верхнего уровня в JSON")

    try:
        return Asset.from_dict(data)
    except Exception as e:
        raise StorageError(f"Ошибка разбора Asset: {e}") from e


# ============================================================
# LIST / DELETE
# ============================================================

def list_assets(folder: Path | None = None) -> list[Asset]:
    """Загрузить все Asset'ы из папки.

    Битые файлы пропускаются с print-предупреждением.
    """
    target_dir = Path(folder) if folder else ASSETS_DIR
    if not target_dir.exists():
        return []

    assets: list[Asset] = []
    for json_file in sorted(target_dir.glob("*.json")):
        # Пропускать служебные файлы (начинаются с _)
        if json_file.name.startswith("_"):
            continue
        try:
            assets.append(load_asset(json_file))
        except StorageError as e:
            print(f"[storage] skip {json_file.name}: {e}")
    return assets


def delete_asset(asset_id: str, folder: Path | None = None) -> bool:
    """Удалить файл Asset'а. Возвращает True, если файл был удалён."""
    target_dir = Path(folder) if folder else ASSETS_DIR
    path = target_dir / f"{asset_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False


def asset_exists(asset_id: str, folder: Path | None = None) -> bool:
    target_dir = Path(folder) if folder else ASSETS_DIR
    return (target_dir / f"{asset_id}.json").exists()
