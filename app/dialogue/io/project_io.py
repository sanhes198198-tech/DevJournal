"""
Сохранение и загрузка project_data.json.

ProjectData — общие данные проекта:
  - characters
  - variables
  - flags

Файл: boards/<проект>/project_data.json
Схема: PROJECT_DATA_SCHEMA_VERSION (независимо от Dialogue Schema)
"""

import json
import os

from ..project_data import (
    ProjectData,
    PROJECT_DATA_SCHEMA_VERSION,
)


PROJECT_DATA_FILE_NAME = "project_data.json"


# =========================================================
# ПУТЬ
# =========================================================

def get_project_data_path(project_folder):
    """Путь к project_data.json внутри проекта."""
    return os.path.join(project_folder, PROJECT_DATA_FILE_NAME)


def project_data_exists(project_folder):
    """True, если файл project_data.json существует."""
    return os.path.exists(
        get_project_data_path(project_folder)
    )


# =========================================================
# СОХРАНЕНИЕ
# =========================================================

def save_project_data(project_data, project_folder):
    """
    Сохраняет ProjectData в JSON.

    Возвращает путь к сохранённому файлу.
    """
    os.makedirs(project_folder, exist_ok=True)

    path = get_project_data_path(project_folder)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            project_data.to_dict(),
            f,
            ensure_ascii=False,
            indent=2,
        )

    return path


# =========================================================
# ЗАГРУЗКА
# =========================================================

def load_project_data(project_folder):
    """
    Загружает ProjectData из JSON.

    Если файла нет — возвращает пустой ProjectData().
    Если JSON битый — возвращает пустой ProjectData().
    Если schema_version новее — пробует загрузить с предупреждением.
    """
    path = get_project_data_path(project_folder)

    if not os.path.exists(path):
        return ProjectData()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return ProjectData()

    if not isinstance(data, dict):
        return ProjectData()

    version = data.get("schema_version", 1)

    # Заготовка под будущие миграции project_data.
    # Сейчас только версия 1.
    if version != PROJECT_DATA_SCHEMA_VERSION:
        # Не падаем — просто пробуем загрузить как есть.
        # Модель сама защищена от неизвестных полей.
        pass

    return ProjectData.from_dict(data)