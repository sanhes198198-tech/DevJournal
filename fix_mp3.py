import json
import subprocess
from pathlib import Path

FILES = [
    "4a02a5eeace1", "d19f23b952f1",
]

for fname in FILES:
    old_json = subprocess.check_output(
        ["git", "show",
         "cb50131:app/vector_editor/assets/" + fname + ".json"]
    ).decode("utf-8")
    old_data = json.loads(old_json)
    old_mp = old_data.get("mountpoints", [])
    old_groups = old_data.get("semantic_groups", {})

    cur_path = Path("app/vector_editor/assets/" + fname + ".json")
    with open(cur_path, encoding="utf-8") as f:
        cur_data = json.load(f)

    if cur_data.get("mountpoints"):
        print(fname + ": SKIP")
        continue

    cur_groups = cur_data.setdefault("semantic_groups", {})

    # Добавляем недостающие группы
    added_groups = 0
    for m in old_mp:
        gid = m.get("semantic_group_id")
        if gid and gid not in cur_groups and gid in old_groups:
            cur_groups[gid] = old_groups[gid]
            added_groups += 1

    # Добавляем mountpoints
    cur_data["mountpoints"] = old_mp

    with open(cur_path, "w", encoding="utf-8") as f:
        json.dump(cur_data, f, indent=2, ensure_ascii=False)

    print(fname + ": restored " + str(len(old_mp)) + " mp, "
          + str(added_groups) + " groups")