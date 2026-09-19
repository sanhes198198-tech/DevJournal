"""
IO layer для модуля диалогов.

Сохранение и загрузка JSON-файлов.
"""

from .project_io import (
    PROJECT_DATA_FILE_NAME,
    get_project_data_path,
    project_data_exists,
    save_project_data,
    load_project_data,
)

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
    # project_data
    "PROJECT_DATA_FILE_NAME",
    "get_project_data_path",
    "project_data_exists",
    "save_project_data",
    "load_project_data",
    # storage
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
