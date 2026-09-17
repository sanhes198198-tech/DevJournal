"""
Единый источник шрифтов и настроек типографики.

Все карточки используют эти функции — чтобы менять шрифт
в одном месте, а не в пяти.
"""

from PySide6.QtGui import QFont


# ---------------------------------------------------------
# Настройки по умолчанию (можно менять здесь)
# ---------------------------------------------------------

FONT_FAMILY = "Roboto"

FONT_SIZE_BODY = 12
FONT_SIZE_TITLE = 14

# ---------------------------------------------------------
# Фабрики шрифтов
# ---------------------------------------------------------


def body_font():
    """
    Шрифт для тела текста (обычный).
    """
    font = QFont(FONT_FAMILY, FONT_SIZE_BODY)
    return font


def title_font():
    """
    Шрифт для заголовка (жирный, чуть больше).
    """
    font = QFont(FONT_FAMILY, FONT_SIZE_TITLE)
    try:
        font.setWeight(QFont.Weight.DemiBold)
    except Exception:
        font.setBold(False)
    return font


def comment_title_font():
    """
    Шрифт для имени автора в комментарии.
    """
    font = QFont(FONT_FAMILY, FONT_SIZE_BODY)
    try:
        font.setWeight(QFont.Weight.DemiBold)
    except Exception:
        font.setBold(False)
    return font


# ---------------------------------------------------------
# Применение шрифта к EditableText
# ---------------------------------------------------------


def apply_to_editable(text_item, role="body"):
    """
    Применяет шрифт к EditableText.

    role:
        "body"           — обычный текст
        "title"          — заголовок
        "comment_title"  — имя автора комментария
    """

    if text_item is None:
        return

    if role == "title":
        text_item.setFont(title_font())

    elif role == "comment_title":
        text_item.setFont(comment_title_font())

    else:
        text_item.setFont(body_font())