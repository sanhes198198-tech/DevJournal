import os

APP_NAME = "DevJournal"

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

BOARDS_DIR = os.path.join(
    BASE_DIR,
    "boards",
)

os.makedirs(
    BOARDS_DIR,
    exist_ok=True,
)


# =============================================================
# SECTIONS (разделы проекта)
# =============================================================

DEFAULT_SECTION = "dnevnik"

SECTIONS = (
    ("dnevnik",    "📖  Дневник"),
    ("mir",        "🌍  Мир"),
    ("personazhi", "👤  Персонажи"),
    ("lokacii",    "🏙  Локации"),
    ("geimpl",     "🎮  Геймплей"),
    ("art",        "🎨  Арт"),
    ("tehnika",    "🔧  Техника"),
)

SECTION_LABELS = {
    slug: label
    for slug, label in SECTIONS
}