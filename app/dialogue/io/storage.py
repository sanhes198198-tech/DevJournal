"""
Сохранение и загрузка диалогов.

Каждый диалог — отдельный JSON-файл.
index.json — список диалогов проекта.
"""

import json
import os

from ..model import Dialogue


# =========================================================
# КОНСТАНТЫ
# =========================================================

DIALOGUES_DIR_NAME = "dialogues"
INDEX_FILE_NAME = "index.json"

DIALOGUE_FORMAT_VERSION = 2


# =========================================================
# ПУТИ
# =========================================================

def get_dialogues_dir(project_folder):
    """Возвращает путь к папке dialogues (без создания)."""
    return os.path.join(project_folder, DIALOGUES_DIR_NAME)


def ensure_dialogues_dir(project_folder):
    """Создаёт папку dialogues, если её нет. Возвращает путь."""
    path = get_dialogues_dir(project_folder)
    os.makedirs(path, exist_ok=True)
    return path


def get_dialogue_path(dialogue_id, project_folder):
    """Путь к JSON-файлу одного диалога."""
    return os.path.join(
        get_dialogues_dir(project_folder),
        f"{dialogue_id}.json",
    )


def get_index_path(project_folder):
    """Путь к index.json."""
    return os.path.join(
        get_dialogues_dir(project_folder),
        INDEX_FILE_NAME,
    )


# =========================================================
# ОДИН ДИАЛОГ
# =========================================================

# =========================================================
# МИГРАЦИИ ФОРМАТА
# =========================================================

def _migrate_v1_to_v2(dialogue_data):
    """
    Миграция данных диалога v1 → v2.

    Добавляет отсутствующие поля, появившиеся в v2:
      - ReplyNode.presentation = {}
      - ChoiceOption.effects = []
      - ChoiceOption.condition = None
      - EndNode.outcome = "end"
      - EndNode.target_dialogue_id = None

    Не трогает существующие поля и ID.
    Возвращает изменённый dialogue_data (тот же объект).
    """
    if not isinstance(dialogue_data, dict):
        return dialogue_data

    nodes = dialogue_data.get("nodes", [])
    if not isinstance(nodes, list):
        return dialogue_data

    for node in nodes:
        if not isinstance(node, dict):
            continue

        ntype = node.get("type")

        if ntype == "reply":
            node.setdefault("presentation", {})

        elif ntype == "choice":
            options = node.get("options", [])
            if isinstance(options, list):
                for opt in options:
                    if not isinstance(opt, dict):
                        continue
                    opt.setdefault("effects", [])
                    opt.setdefault("condition", None)

        elif ntype == "end":
            node.setdefault("outcome", "end")
            node.setdefault("target_dialogue_id", None)

    return dialogue_data


def save_dialogue(dialogue, project_folder):
    """
    Сохраняет диалог в JSON-файл.

    Возвращает путь к сохранённому файлу.
    """
    ensure_dialogues_dir(project_folder)

    path = get_dialogue_path(dialogue.id, project_folder)

    data = {
        "version": DIALOGUE_FORMAT_VERSION,
        "dialogue": dialogue.to_dict(),
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return path


def load_dialogue(dialogue_id, project_folder):
    """
    Загружает диалог из JSON.

    Возвращает Dialogue или None, если файла нет.
    """
    path = get_dialogue_path(dialogue_id, project_folder)

    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    version = data.get("version", 1)
    dialogue_data = data.get("dialogue", {})

    # Явный пайплайн миграций: v1 → v2 → ... → current
    # Каждая миграция — отдельная функция. Новые версии — новые шаги.
    if version == 1:
        dialogue_data = _migrate_v1_to_v2(dialogue_data)
        version = 2

    # Если версия неизвестна (например, новее) — пробуем загрузить как есть.
    # Модель сама подставит дефолты для отсутствующих полей.

    return Dialogue.from_dict(dialogue_data)


def dialogue_exists(dialogue_id, project_folder):
    """True, если файл диалога существует."""
    return os.path.exists(
        get_dialogue_path(dialogue_id, project_folder)
    )


def delete_dialogue(dialogue_id, project_folder):
    """
    Удаляет файл диалога.

    Возвращает True, если файл был и удалён, иначе False.
    """
    path = get_dialogue_path(dialogue_id, project_folder)

    if not os.path.exists(path):
        return False

    os.remove(path)
    return True


def list_dialogue_ids(project_folder):
    """
    Возвращает список ID диалогов (по файлам в папке).

    index.json не учитывается.
    """
    dialogues_dir = get_dialogues_dir(project_folder)

    if not os.path.isdir(dialogues_dir):
        return []

    result = []

    for name in os.listdir(dialogues_dir):
        if not name.endswith(".json"):
            continue
        if name == INDEX_FILE_NAME:
            continue
        result.append(name[:-5])  # убираем .json

    result.sort()
    return result


# =========================================================
# INDEX
# =========================================================

def default_index():
    """Пустой index с корректной структурой."""
    return {
        "version": DIALOGUE_FORMAT_VERSION,
        "dialogue_ids": [],
        "last_opened": None,
    }


def save_index(index_data, project_folder):
    """Сохраняет index.json."""
    ensure_dialogues_dir(project_folder)
    path = get_index_path(project_folder)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)

    return path


def load_index(project_folder):
    """
    Загружает index.json.

    Если файла нет — возвращает default_index().
    """
    path = get_index_path(project_folder)

    if not os.path.exists(path):
        return default_index()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return default_index()

    # Гарантируем все поля
    result = default_index()
    result.update(data)
    return result


def rebuild_index(project_folder):
    """
    Пересобирает index на основе реальных файлов в папке.

    Полезно, если index.json потерян или рассинхронизирован.
    """
    ids = list_dialogue_ids(project_folder)

    existing = load_index(project_folder)
    last_opened = existing.get("last_opened")

    if last_opened not in ids:
        last_opened = None

    index_data = {
        "version": DIALOGUE_FORMAT_VERSION,
        "dialogue_ids": ids,
        "last_opened": last_opened,
    }

    save_index(index_data, project_folder)
    return index_data
