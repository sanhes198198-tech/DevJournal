import json
import subprocess
from pathlib import Path

# Файлы + mp где группы ЖИВЫ
RESTORE = [
    "0b83487c4eea", "2d7f96953f11", "3ec907f2b564",
]

for fname in RESTORE:
    old_json = subprocess.check_output(
        ["git", "show",
         "cb50131:app/vector_editor/assets/" + fname + ".json"]
    ).decode("utf-8")
    old_data = json.loads(old_json)
    old_mp = old_data.get("mountpoints", [])

    cur_path = Path("app/vector_editor/assets/" + fname + ".json")
    with open(cur_path, encoding="utf-8") as f:
        cur_data = json.load(f)

    if cur_data.get("mountpoints"):
        print(fname + ": SKIP (already has mp)")
        continue

    cur_data["mountpoints"] = old_mp

    with open(cur_path, "w", encoding="utf-8") as f:
        json.dump(cur_data, f, indent=2, ensure_ascii=False)

    print(fname + ": restored " + str(len(old_mp)) + " mp")