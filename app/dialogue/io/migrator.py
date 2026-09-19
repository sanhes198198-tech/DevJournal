"""
Project-wide миграция v2 -> v3.

READ-ONLY анализ. Ничего не пишет на диск.

Реальная запись будет добавлена ПОСЛЕ обновления модели
(node.py) до поддержки v3-полей — иначе загрузка сломается.

Принцип атомарности для будущей записи:
  1. Прочитать всё
  2. Построить speaker_map
  3. Подготовить мигрированные данные в памяти
  4. Записать project_data.json
  5. Записать диалоги
  6. Обновить index.json
Никаких частичных состояний "диалог 1 записан, диалог 2 упал".
"""

import copy
import json
import os

from .storage import (
    get_dialogues_dir,
    get_dialogue_path,
    INDEX_FILE_NAME,
    _migrate_v1_to_v2,
    _migrate_v2_to_v3,
    build_speaker_map,
    rebuild_index,
)
from .project_io import save_project_data, load_project_data
from ..project_data import Character


def plan_project_v2_to_v3_migration(project_folder):
    """
    READ-ONLY. Анализ проекта для миграции v2 -> v3.

    Возвращает отчёт-план:
    {
        "total_dialogues": int,
        "v2_dialogues": [dialogue_id, ...],
        "v3_dialogues": [dialogue_id, ...],
        "errors": [{"dialogue_id": ..., "error": ...}, ...],
        "speakers_found": [raw_name, ...],
        "planned_speaker_map": {raw_name: slug, ...},
        "planned_characters": [slug, ...],
        "planned_migrated_dialogues": {
            dialogue_id: {"version": 3, "dialogue": {...}},
            ...
        },
    }
    """
    report = {
        "total_dialogues": 0,
        "v2_dialogues": [],
        "v3_dialogues": [],
        "errors": [],
        "speakers_found": [],
        "planned_speaker_map": {},
        "planned_characters": [],
        "planned_migrated_dialogues": {},
    }

    dialogues_dir = get_dialogues_dir(project_folder)
    if not os.path.isdir(dialogues_dir):
        return report

    # --- Собрать все ID ---
    ids = []
    for name in os.listdir(dialogues_dir):
        if not name.endswith(".json"):
            continue
        if name == INDEX_FILE_NAME:
            continue
        ids.append(name[:-5])

    ids.sort()
    report["total_dialogues"] = len(ids)

    # --- Прочитать всё в память ---
    raw_data = {}       # {dialogue_id: (version, raw_dict)}
    v2_speakers = []

    for did in ids:
        path = get_dialogue_path(did, project_folder)
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            report["errors"].append({
                "dialogue_id": did,
                "error": f"read failed: {e!r}",
            })
            continue

        if not isinstance(raw, dict):
            report["errors"].append({
                "dialogue_id": did,
                "error": "not a dict",
            })
            continue

        version = raw.get("version", 1)
        raw_data[did] = (version, raw)

        # Собрать speakers из v2-диалогов
        if version < 3:
            dialogue_data = raw.get("dialogue", {})
            if isinstance(dialogue_data, dict):
                nodes = dialogue_data.get("nodes", [])
                if isinstance(nodes, list):
                    for node in nodes:
                        if not isinstance(node, dict):
                            continue
                        if node.get("type") == "reply":
                            sp = node.get("speaker", "")
                            if isinstance(sp, str) and sp.strip():
                                v2_speakers.append(sp)

    # --- Разделить v2/v3 ---
    for did, (version, _) in raw_data.items():
        if version >= 3:
            report["v3_dialogues"].append(did)
        else:
            report["v2_dialogues"].append(did)

    report["v2_dialogues"].sort()
    report["v3_dialogues"].sort()

    report["speakers_found"] = sorted(set(v2_speakers))

    # --- Построить speaker_map ---
    speaker_map = build_speaker_map(v2_speakers)
    report["planned_speaker_map"] = dict(speaker_map)

    # --- Планируемые characters ---
    planned_chars = []
    slug_to_name = {}   # slug -> лучшее raw_name

    for raw_name in sorted(speaker_map.keys()):
        slug = speaker_map[raw_name]

        if slug not in slug_to_name:
            slug_to_name[slug] = raw_name
        else:
            # Предпочитаем форму с заглавной буквы
            current = slug_to_name[slug]
            if (
                current
                and not current[0].isupper()
                and raw_name
                and raw_name[0].isupper()
            ):
                slug_to_name[slug] = raw_name

    for slug in sorted(slug_to_name.keys()):
        planned_chars.append(slug)

    report["planned_characters"] = planned_chars
    report["planned_character_names"] = slug_to_name

    # --- Подготовить мигрированные данные (в памяти) ---
    for did in report["v2_dialogues"]:
        version, raw = raw_data[did]
        dialogue_data = raw.get("dialogue", {})

        if not isinstance(dialogue_data, dict):
            continue

        # Копируем, чтобы не мутировать оригинал
        work = copy.deepcopy(dialogue_data)

        if version == 1:
            work = _migrate_v1_to_v2(work)

        work = _migrate_v2_to_v3(work, speaker_map)

        report["planned_migrated_dialogues"][did] = {
            "version": 3,
            "dialogue": work,
        }

    return report

# =========================================================
# APPLY MIGRATION (запись на диск)
# =========================================================

def apply_project_migration(project_folder):
    """
    Реальная миграция проекта v2/v1 -> v3 с записью на диск.

    Порядок (атомарная логика):
      1. plan (read-only) — что мигрировать
      2. Подготовить ProjectData в памяти
      3. Записать project_data.json
      4. Записать все мигрированные диалоги
      5. Обновить index.json

    Возвращает dict-отчёт:
      {
        "applied": bool,
        "reason": str | None,
        "migrated": [dialogue_id, ...],
        "characters_created": [slug, ...],
        "errors": [...]
      }
    """

    report = plan_project_v2_to_v3_migration(project_folder)

    # Никакой миграции, если в плане ошибки
    if report["errors"]:
        return {
            "applied": False,
            "reason": "plan has errors",
            "migrated": [],
            "characters_created": [],
            "errors": report["errors"],
        }

    if not report["v2_dialogues"]:
        return {
            "applied": False,
            "reason": "no v2 dialogues",
            "migrated": [],
            "characters_created": [],
            "errors": [],
        }

    # --- Загружаем существующий ProjectData ---
    try:
        pd = load_project_data(project_folder)
    except Exception as e:
        return {
            "applied": False,
            "reason": f"load_project_data failed: {e!r}",
            "migrated": [],
            "characters_created": [],
            "errors": [],
        }

    # --- Обогащаем ProjectData персонажами ---
    planned_names = report.get("planned_character_names", {})
    created_slugs = []

    for slug in report["planned_characters"]:
        if slug in pd.characters:
            continue

        name = planned_names.get(slug, slug)
        pd.add_character(Character(character_id=slug, name=name))
        created_slugs.append(slug)

    # --- Атомарная запись ---
    try:
        save_project_data(pd, project_folder)

        for did, data in report["planned_migrated_dialogues"].items():
            path = get_dialogue_path(did, project_folder)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        rebuild_index(project_folder)

    except Exception as e:
        return {
            "applied": False,
            "reason": f"write failed: {e!r}",
            "migrated": [],
            "characters_created": created_slugs,
            "errors": [],
        }

    return {
        "applied": True,
        "reason": None,
        "migrated": list(report["planned_migrated_dialogues"].keys()),
        "characters_created": created_slugs,
        "errors": [],
    }
