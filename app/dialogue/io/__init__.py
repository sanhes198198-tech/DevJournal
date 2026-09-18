"""
IO layer для модуля диалогов.

Сохранение и загрузка JSON-файлов.
"""

from .storage import (
    DIALOGUES_DIR_NAME,
    INDEX_FILE_NAME,
    DIALOGUE_FORMAT_VERSION,
    get_dialogues_dir,
    ensure_dialogues_dir,
    get_dialogue_path,
    get_index_path,
    save_dialogue,
    load_dialogue,
    dialogue_exists,
    delete_dialogue,
    list_dialogue_ids,
    default_index,
    save_index,
    load_index,
    rebuild_index,
)


__all__ = [
    "DIALOGUES_DIR_NAME",
    "INDEX_FILE_NAME",
    "DIALOGUE_FORMAT_VERSION",
    "get_dialogues_dir",
    "ensure_dialogues_dir",
    "get_dialogue_path",
    "get_index_path",
    "save_dialogue",
    "load_dialogue",
    "dialogue_exists",
    "delete_dialogue",
    "list_dialogue_ids",
    "default_index",
    "save_index",
    "load_index",
    "rebuild_index",
]
