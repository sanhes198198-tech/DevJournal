import json
import subprocess
from pathlib import Path

FILES = [
    "0b83487c4eea", "2d7f96953f11", "3ec907f2b564",
    "4a02a5eeace1", "c2dd0d912a21", "d19f23b952f1",
]

for fname in FILES:
    try:
        old_json = subprocess.check_output(
            ["git", "show",
             "cb50131:app/vector_editor/assets/" + fname + ".json"]
        ).decode("utf-8")
    except subprocess.CalledProcessError:
        print(fname + ": not in cb50131")
        continue

    old_data = json.loads(old_json)
    old_mp = old_data.get("mountpoints", [])

    cur_path = Path("app/vector_editor/assets/" + fname + ".json")
    with open(cur_path, encoding="utf-8") as f:
        cur_data = json.load(f)

    cur_groups = cur_data.get("semantic_groups", {})
    cur_mp = cur_data.get("mountpoints", [])

    print("")
    print("=== " + fname + " ===")
    print("  cb50131: " + str(len(old_mp)) + " mp, current: " + str(len(cur_mp)))

    if len(cur_mp) > 0:
        print("  SKIP - уже есть mountpoints")
        continue

    for m in old_mp:
        gid = m.get("semantic_group_id")
        mp_id = m.get("id")
        if gid and gid not in cur_groups:
            print("  WARN: " + str(mp_id) + " группа " + str(gid) + " - НЕ существует")
        else:
            print("  OK:   " + str(mp_id) + " группа " + str(gid) + " есть")