"""
Сохранение и загрузка architecture.json.

Никаких миграций в M0. schema_version проверяется строго.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..model.architecture import ArchitectureModel, SCHEMA_VERSION


ARCHITECTURE_FILENAME = "architecture.json"


class StorageError(Exception):
    """Ошибка сохранения или загрузки."""


class UnsupportedSchemaError(StorageError):
    """schema_version не поддерживается."""


def get_architecture_path(project_folder: Path) -> Path:
    """Путь к architecture.json внутри папки проекта."""
    return Path(project_folder) / ARCHITECTURE_FILENAME


def file_exists(project_folder: Path) -> bool:
    return get_architecture_path(project_folder).exists()


def save_model(model: ArchitectureModel, path: Path) -> None:
    """Атомарно записывает модель в JSON.

    Пишем во временный файл, затем os.replace.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = model.to_dict()
    tmp = path.with_suffix(path.suffix + ".tmp")

    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        tmp.replace(path)
    except OSError as e:
        raise StorageError(f"Не удалось записать файл: {e}") from e


def load_model(path: Path) -> ArchitectureModel:
    """Читает модель из JSON.

    Кидает StorageError при любой проблеме.
    Не пытается «починить» — вызывающий решает, что делать.
    """
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

    sv = data.get("schema_version")
    if sv != SCHEMA_VERSION:
        raise UnsupportedSchemaError(
            f"schema_version={sv!r}, поддерживается только {SCHEMA_VERSION}"
        )

    return ArchitectureModel.from_dict(data)
