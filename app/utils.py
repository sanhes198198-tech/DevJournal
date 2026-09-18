import os

from .config import BOARDS_DIR


def safe_project_name(name):
    invalid = '<>:"/\\|?*'

    result = "".join(
        "_"
        if c in invalid
        else c
        for c in name
    )

    result = result.strip()

    if not result:
        result = "Project"

    return result


def ensure_project_folder(name):
    name = safe_project_name(name)

    folder = os.path.join(
        BOARDS_DIR,
        name,
    )

    os.makedirs(
        folder,
        exist_ok=True,
    )

    os.makedirs(
        os.path.join(
            folder,
            "images",
        ),
        exist_ok=True,
    )

    os.makedirs(
        os.path.join(
            folder,
            "sections",
        ),
        exist_ok=True,
    )

    return folder