"""
Модуль чтения и записи доски проекта.

Содержит функции save_board и load_board.

Сохраняет:
- содержимое карточек;
- HTML-форматирование текста;
- режим сетки;
- масштаб Canvas;
- положение viewport;
- card_id объектов;
- стрелки и их соединения;
- положение свободного конца стрелки;
- изгиб стрелки;
- рамки и их содержимое.

Логика сохранения и восстановления стрелок
вынесена в arrow_persistence.py.
Логика сохранения и восстановления рамок
вынесена в frame_persistence.py.
"""

import json
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QMessageBox

from ..utils import ensure_project_folder

from ..cards.text.text_card import TextCard
from ..cards.heading.heading_card import HeadingCard
from ..cards.image_text.image_card import ImageTextCard
from ..cards.comment.comment_card import CommentCard
from ..cards.image.image_item import ImageItem
from ..cards.color.color_item import ColorItem
from ..cards.video.video_text_item import VideoTextItem

from ..items.file_item import FileItem

from .arrow_persistence import collect_arrows, restore_arrows
from .frame_persistence import collect_frames, restore_frames
from .card_ids import generate_card_id


# =============================================================
# HELPERS
# =============================================================

def _get_item_id(item):
    """Возвращает card_id элемента."""

    if item is None:
        return None

    return getattr(item, "card_id", None)


def _get_text_data(text_item):
    """Возвращает plain text и HTML QTextDocument."""

    if text_item is None:
        return {
            "text": "",
            "html": "",
        }

    return {
        "text": text_item.toPlainText(),
        "html": text_item.toHtml(),
    }


def clean_html_colors(html):
    """
    Убирает color:, font-weight:, font-family: из HTML.
    Нужно, чтобы defaultTextColor и typography работали.
    """

    if not html:
        return html

    import re

    # color: #xxxxxx; или color:#xxxxxx;
    html = re.sub(
        r"\s*color\s*:\s*#[0-9a-fA-F]+\s*;?",
        "",
        html,
    )

    # font-weight: 700; и т.п.
    html = re.sub(
        r"\s*font-weight\s*:\s*\d+\s*;?",
        "",
        html,
    )

    # font-family: 'Xxx'; и т.п.
    html = re.sub(
        r"\s*font-family\s*:\s*'[^']*'\s*;?",
        "",
        html,
    )

    return html


def _restore_text_item(text_item, text, html):
    """Восстанавливает содержимое EditableText."""

    if text_item is None:
        return

    if html:
        cleaned = clean_html_colors(html)
        text_item.setHtml(cleaned)
    else:
        text_item.setPlainText(text or "")


def _add_card_text_data(card_data, title_item, body_item):
    """Добавляет текст и HTML-форматирование карточки."""

    title_data = _get_text_data(title_item)
    body_data = _get_text_data(body_item)

    card_data["title"] = title_data["text"]
    card_data["title_html"] = title_data["html"]
    card_data["text"] = body_data["text"]
    card_data["text_html"] = body_data["html"]


def _restore_card_text(card, item_data):
    """Восстанавливает форматирование title/body карточки."""

    if card is None:
        return

    title_item = getattr(card, "title_item", None)
    body_item = getattr(card, "body_item", None)

    title_text = item_data.get("title", "")
    title_html = item_data.get("title_html", "")

    body_text = item_data.get("text", "")
    body_html = item_data.get("text_html", "")

    _restore_text_item(
        title_item,
        title_text,
        title_html,
    )

    _restore_text_item(
        body_item,
        body_text,
        body_html,
    )


def _ensure_card_ids(canvas):
    """
    Гарантирует, что у каждой сохраняемой карточки есть card_id.

    Карточки, созданные в текущей сессии через фабрики,
    не получают card_id. Из-за этого стрелки, которые на них
    ссылаются, не могут быть сохранены (serialize_arrow
    возвращает None). Присваиваем id здесь — до того, как
    items попадут в JSON.
    """

    saveable_types = (
        TextCard,
        HeadingCard,
        ImageTextCard,
        CommentCard,
        ColorItem,
        VideoTextItem,
        ImageItem,
        FileItem,
    )

    generated = 0

    try:
        scene_items = canvas.scene.items()
    except Exception:
        return

    for scene_item in scene_items:

        if not isinstance(scene_item, saveable_types):
            continue

        try:
            existing = getattr(scene_item, "card_id", None)
        except Exception:
            existing = None

        if existing is not None:
            try:
                if str(existing).strip():
                    continue
            except Exception:
                pass

        try:
            new_id = generate_card_id()
            scene_item.card_id = new_id
            generated += 1
        except Exception as exc:
            print(
                f"[SAVE] ensure card_id failed for "
                f"{type(scene_item).__name__}: {exc!r}"
            )

    if generated:
        print(
            f"[SAVE] assigned card_id to {generated} items"
        )


# =============================================================
# SAVE
# =============================================================

def save_board(canvas):

    if not canvas.main_window.project_name:
        return

    project_folder = ensure_project_folder(
        canvas.main_window.project_name
    )

    board_path = os.path.join(
        project_folder,
        "board.json",
    )

    view_state = canvas.get_view_state()

    # =========================================================
    # ENSURE card_id НА ВСЕХ КАРТОЧКАХ
    # =========================================================
    # Это нужно сделать ДО формирования data["items"],
    # иначе стрелки, ссылающиеся на карточки без card_id,
    # не сохранятся.

    _ensure_card_ids(canvas)

    data = {
        "version": 12,
        "project_name": canvas.main_window.project_name,
        "grid_mode": canvas.grid_mode,
        "view": view_state,
        "items": [],
        "arrows": [],
        "frames": [],
    }

    # =========================================================
    # ITEMS
    # =========================================================

    for item in canvas.scene.items():

        # =====================================================
        # TEXT CARD
        # =====================================================

        if isinstance(item, TextCard):

            rect = item.rect()

            card_data = {
                "type": "card",
                "card_id": _get_item_id(item),
                "x": item.pos().x(),
                "y": item.pos().y(),
                "width": rect.width(),
                "height": rect.height(),
                "color": canvas._get_item_color(item),
                "card_type": "text",
            }

            _add_card_text_data(
                card_data,
                item.title_item,
                item.body_item,
            )

            data["items"].append(card_data)

        # =====================================================
        # HEADING CARD
        # =====================================================

        elif isinstance(item, HeadingCard):

            rect = item.rect()

            card_data = {
                "type": "card",
                "card_id": _get_item_id(item),
                "x": item.pos().x(),
                "y": item.pos().y(),
                "width": rect.width(),
                "height": rect.height(),
                "color": canvas._get_item_color(item),
                "card_type": "heading",
            }

            _add_card_text_data(
                card_data,
                item.title_item,
                item.body_item,
            )

            data["items"].append(card_data)

        # =====================================================
        # IMAGE + TEXT CARD
        # =====================================================

        elif isinstance(item, ImageTextCard):

            rect = item.rect()

            card_data = {
                "type": "card",
                "card_id": _get_item_id(item),
                "x": item.pos().x(),
                "y": item.pos().y(),
                "width": rect.width(),
                "height": rect.height(),
                "color": canvas._get_item_color(item),
                "card_type": "image_text",
                "image_path": item.image_path,
            }

            _add_card_text_data(
                card_data,
                item.title_item,
                item.body_item,
            )

            data["items"].append(card_data)

        # =====================================================
        # COMMENT
        # =====================================================

        elif isinstance(item, CommentCard):

            rect = item.rect()

            card_data = {
                "type": "card",
                "card_id": _get_item_id(item),
                "x": item.pos().x(),
                "y": item.pos().y(),
                "width": rect.width(),
                "height": rect.height(),
                "color": canvas._get_item_color(item),
                "card_type": "comment",
            }

            _add_card_text_data(
                card_data,
                item.title_item,
                item.body_item,
            )

            data["items"].append(card_data)

        # =====================================================
        # COLOR ITEM
        # =====================================================

        elif isinstance(item, ColorItem):

            rect = item.rect()

            color_data = {
                "type": "card",
                "card_id": _get_item_id(item),
                "x": item.pos().x(),
                "y": item.pos().y(),
                "width": rect.width(),
                "height": rect.height(),
                "title": "",
                "text": "",
                "color": canvas._get_item_color(item),
                "card_type": "color",
            }

            data["items"].append(color_data)

        # =====================================================
        # VIDEO
        # =====================================================

        elif isinstance(item, VideoTextItem):

            title_data = _get_text_data(item.title_item)
            body_data = _get_text_data(item.body_item)

            data["items"].append({
                "type": "video_text",
                "card_id": _get_item_id(item),
                "x": item.pos().x(),
                "y": item.pos().y(),
                "width": item.item_width,
                "height": item.item_height,
                "title": title_data["text"],
                "title_html": title_data["html"],
                "text": body_data["text"],
                "text_html": body_data["html"],
                "video_path": item.video_path,
                "color": canvas._get_item_color(item),
            })

        # =====================================================
        # IMAGE
        # =====================================================

        elif isinstance(item, ImageItem):

            data["items"].append({
                "type": "image",
                "card_id": _get_item_id(item),
                "x": item.pos().x(),
                "y": item.pos().y(),
                "path": item.image_path,
                "width": item.pixmap().width(),
                "height": item.pixmap().height(),
                "color": canvas._get_item_color(item),
            })

        # =====================================================
        # FILE
        # =====================================================

        elif isinstance(item, FileItem):

            data["items"].append({
                "type": "file",
                "card_id": _get_item_id(item),
                "x": item.pos().x(),
                "y": item.pos().y(),
                "path": item.file_path,
                "name": item.file_name,
            })

    # =========================================================
    # ARROWS
    # =========================================================

    data["arrows"] = collect_arrows(canvas.scene)

    # =========================================================
    # FRAMES
    # =========================================================

    data["frames"] = collect_frames(canvas.scene)

    # =========================================================
    # WRITE JSON
    # =========================================================

    try:

        with open(
            board_path,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4,
            )

        if canvas.main_window:
            canvas.main_window.update_status(
                "Сохранено"
            )

    except Exception as e:

        QMessageBox.warning(
            canvas.main_window,
            "Ошибка сохранения",
            str(e),
        )


# =============================================================
# LOAD
# =============================================================

def load_board(canvas, project_name):

    project_folder = ensure_project_folder(
        project_name
    )

    board_path = os.path.join(
        project_folder,
        "board.json",
    )

    canvas.scene.clear()

    if not os.path.exists(board_path):

        canvas.main_window.project_name = project_name
        return

    try:

        with open(
            board_path,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        # =====================================================
        # GRID
        # =====================================================

        canvas.grid_mode = data.get(
            "grid_mode",
            "dots",
        )

        # =====================================================
        # VIEW STATE
        # =====================================================

        view_state = data.get(
            "view",
            {},
        )

        # =====================================================
        # ITEMS
        # =====================================================

        items = data.get(
            "items",
            [],
        )

        item_by_id = {}

        for item_data in items:

            item_type = item_data.get(
                "type"
            )

            # =================================================
            # CARD
            # =================================================

            if item_type == "card":

                card_type = item_data.get(
                    "card_type",
                    "text",
                )

                saved_id = item_data.get(
                    "card_id",
                    None,
                )

                card = canvas.add_card(
                    title=item_data.get(
                        "title",
                        "Новая карточка",
                    ),
                    text=item_data.get(
                        "text",
                        "",
                    ),
                    x=item_data.get(
                        "x",
                        0,
                    ),
                    y=item_data.get(
                        "y",
                        0,
                    ),
                    width=item_data.get(
                        "width",
                        280,
                    ),
                    height=item_data.get(
                        "height",
                        180,
                    ),
                    color=item_data.get(
                        "color",
                        "#FFFFFF",
                    ),
                    card_type=card_type,
                    image_path=item_data.get(
                        "image_path",
                        "",
                    ),
                    card_id=saved_id,
                )

                _restore_card_text(
                    card,
                    item_data,
                )

                saved_color = item_data.get(
                    "color",
                    "#FFFFFF",
                )

                if hasattr(
                    card,
                    "set_card_color",
                ):

                    try:
                        card.set_card_color(
                            saved_color
                        )
                    except Exception:
                        pass

                if saved_id is not None:
                    item_by_id[saved_id] = card

            # =================================================
            # VIDEO
            # =================================================

            elif item_type == "video_text":

                relative_path = item_data.get(
                    "video_path",
                    "",
                )

                if not relative_path:
                    continue

                if os.path.isabs(relative_path):
                    video_path = relative_path
                else:
                    video_path = os.path.join(
                        project_folder,
                        relative_path,
                    )

                if not os.path.exists(video_path):
                    continue

                item = VideoTextItem(
                    title=item_data.get(
                        "title",
                        "Заголовок",
                    ),
                    text=item_data.get(
                        "text",
                        "",
                    ),
                    video_path=video_path,
                    width=item_data.get(
                        "width",
                        360,
                    ),
                    height=item_data.get(
                        "height",
                        420,
                    ),
                )

                item.video_path = relative_path
                item.runtime_video_path = video_path

                item.set_card_color(
                    item_data.get(
                        "color",
                        "#FFFFFF",
                    )
                )

                saved_id = item_data.get(
                    "card_id",
                    None,
                )

                if saved_id is not None:
                    item.card_id = saved_id

                _restore_text_item(
                    item.title_item,
                    item_data.get(
                        "title",
                        "",
                    ),
                    item_data.get(
                        "title_html",
                        "",
                    ),
                )

                _restore_text_item(
                    item.body_item,
                    item_data.get(
                        "text",
                        "",
                    ),
                    item_data.get(
                        "text_html",
                        "",
                    ),
                )

                item.setPos(
                    item_data.get(
                        "x",
                        0,
                    ),
                    item_data.get(
                        "y",
                        0,
                    ),
                )

                canvas.scene.addItem(item)

                if saved_id is not None:
                    item_by_id[saved_id] = item

            # =================================================
            # IMAGE
            # =================================================

            elif item_type == "image":

                relative_path = item_data.get(
                    "path",
                    "",
                )

                if not relative_path:
                    continue

                if os.path.isabs(relative_path):
                    image_path = relative_path
                else:
                    image_path = os.path.join(
                        project_folder,
                        relative_path,
                    )

                if not os.path.exists(image_path):
                    continue

                pixmap = QPixmap(image_path)

                if pixmap.isNull():
                    continue

                item = ImageItem(
                    pixmap,
                    relative_path,
                )

                saved_width = item_data.get(
                    "width"
                )

                saved_height = item_data.get(
                    "height"
                )

                if saved_width and saved_height:

                    scaled = pixmap.scaled(
                        int(saved_width),
                        int(saved_height),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )

                    item.setPixmap(scaled)

                item.saved_scale = (
                    item.pixmap().width()
                    / max(
                        1,
                        item.original_width,
                    )
                )

                saved_color = item_data.get(
                    "color",
                    "#00000000",
                )

                if hasattr(
                    item,
                    "set_card_color",
                ):

                    try:
                        item.set_card_color(
                            saved_color
                        )
                    except Exception:
                        pass

                saved_id = item_data.get(
                    "card_id",
                    None,
                )

                if saved_id is not None:
                    item.card_id = saved_id

                item.setPos(
                    item_data.get(
                        "x",
                        0,
                    ),
                    item_data.get(
                        "y",
                        0,
                    ),
                )

                canvas.scene.addItem(item)

                if saved_id is not None:
                    item_by_id[saved_id] = item

            # =================================================
            # FILE
            # =================================================

            elif item_type == "file":

                relative_path = item_data.get(
                    "path",
                    "",
                )

                if not relative_path:
                    continue

                if os.path.isabs(relative_path):
                    file_path = relative_path
                else:
                    file_path = os.path.join(
                        project_folder,
                        relative_path,
                    )

                if not os.path.exists(file_path):
                    continue

                file_name = item_data.get(
                    "name",
                    os.path.basename(file_path),
                )

                item = FileItem(
                    file_path=relative_path,
                    file_name=file_name,
                )

                item.runtime_file_path = file_path

                saved_id = item_data.get(
                    "card_id",
                    None,
                )

                if saved_id is not None:
                    item.card_id = saved_id

                item.setPos(
                    item_data.get(
                        "x",
                        0,
                    ),
                    item_data.get(
                        "y",
                        0,
                    ),
                )

                canvas.scene.addItem(item)

                if saved_id is not None:
                    item_by_id[saved_id] = item

        # =====================================================
        # RESTORE ARROWS
        # =====================================================

        arrows = data.get(
            "arrows",
            [],
        )

        restore_arrows(
            canvas,
            arrows,
            item_by_id,
        )

        # =====================================================
        # RESTORE FRAMES
        # =====================================================

        frames_data = data.get(
            "frames",
            [],
        )

        restore_frames(
            canvas,
            frames_data,
            item_by_id,
        )

        # =====================================================
        # PROJECT NAME
        # =====================================================

        canvas.main_window.project_name = project_name

        # =====================================================
        # RESTORE VIEW
        # =====================================================

        canvas.restore_view_state(
            view_state
        )

        # =====================================================
        # STATUS
        # =====================================================

        canvas.main_window.update_status(
            "Проект загружен"
        )

        canvas.viewport().update()

    except Exception as e:

        QMessageBox.warning(
            canvas.main_window,
            "Ошибка загрузки",
            str(e),
        )