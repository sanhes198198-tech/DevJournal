"""Clipboard logic for cards: serialize / paste / select all."""


# Внутренние элементы карточек — не копируем / не выделяем.
INTERNAL_TYPE_NAMES = frozenset((
    "EditableText",
    "CardTextItem",
    "QGraphicsTextItem",
    "QGraphicsRectItem",
    "QGraphicsPixmapItem",
    "FrameOverlay",
    "FrameItem",  # рамки — не выделяем/не копируем
    "ArrowItem",
    "RoutedArrow",
    "ArrowBendHandle",
    "SnapOverlay",
    "ColorRing",
))


def is_internal(item):
    if item is None:
        return True

    try:
        return type(item).__name__ in INTERNAL_TYPE_NAMES
    except Exception:
        return True


def get_selectable_items(scene):
    """Все items сцены, которые можно выделить / копировать."""

    if scene is None:
        return []

    result = []

    for item in scene.items():

        if is_internal(item):
            continue

        # Должен иметь card_id или быть копируемым
        if not hasattr(item, "pos"):
            continue

        result.append(item)

    return result


# =========================================================
# SERIALIZE
# =========================================================

def serialize_item(item):
    """Возвращает dict с данными карточки или None."""

    if item is None:
        return None

    try:
        from .cards.text.text_card import TextCard
        from .cards.heading.heading_card import HeadingCard
        from .cards.comment.comment_card import CommentCard
        from .cards.image_text.image_card import ImageTextCard
        from .cards.color.color_item import ColorItem
        from .cards.video.video_text_item import VideoTextItem
        from .cards.image.image_item import ImageItem
        from .items.file_item import FileItem
    except Exception:
        return None

    try:
        pos = item.pos()
    except Exception:
        return None

    # -------- Card-based cards --------
    if isinstance(item, (TextCard, HeadingCard, CommentCard, ImageTextCard)):

        try:
            rect = item.rect()
            w = rect.width()
            h = rect.height()
        except Exception:
            bbox = item.sceneBoundingRect()
            w = bbox.width()
            h = bbox.height()

        data = {
            "type": type(item).__name__,
            "x": pos.x() + 20.0,
            "y": pos.y() + 20.0,
            "width": w,
            "height": h,
            "color": getattr(item, "card_color", "#FFFFFF"),
            "title": getattr(item, "title_text", ""),
            "text": getattr(item, "body_text", ""),
        }

        if isinstance(item, ImageTextCard):
            data["image_path"] = getattr(item, "image_path", "")

        return data

    if isinstance(item, ColorItem):

        try:
            rect = item.rect()
            w = rect.width()
            h = rect.height()
        except Exception:
            w = 120
            h = 120

        return {
            "type": "ColorItem",
            "x": pos.x() + 20.0,
            "y": pos.y() + 20.0,
            "width": w,
            "height": h,
            "color": getattr(item, "card_color", "#FFFFFF"),
        }

    if isinstance(item, VideoTextItem):

        w = getattr(item, "item_width", None)
        h = getattr(item, "item_height", None)

        if w is None or h is None:
            bbox = item.sceneBoundingRect()
            w = bbox.width()
            h = bbox.height()

        return {
            "type": "VideoTextItem",
            "x": pos.x() + 20.0,
            "y": pos.y() + 20.0,
            "width": w,
            "height": h,
            "color": getattr(item, "card_color", "#FFFFFF"),
            "title": getattr(item, "title_text", ""),
            "text": getattr(item, "body_text", ""),
            "video_path": getattr(item, "video_path", ""),
        }

    if isinstance(item, ImageItem):

        return {
            "type": "ImageItem",
            "x": pos.x() + 20.0,
            "y": pos.y() + 20.0,
            "image_path": getattr(item, "image_path", ""),
        }

    if isinstance(item, FileItem):

        return {
            "type": "FileItem",
            "x": pos.x() + 20.0,
            "y": pos.y() + 20.0,
            "file_path": getattr(item, "file_path", ""),
        }

    return None


# =========================================================
# PASTE
# =========================================================

def paste_cards_into_canvas(canvas, clipboard):
    """Создаёт карточки из clipboard. Возвращает список новых items."""

    if canvas is None or not clipboard:
        return []

    scene = canvas.scene

    if scene is None:
        return []

    new_items = []

    for data in clipboard:

        try:
            item = _create_item(canvas, data)
        except Exception as exc:
            print(f"[CLIPBOARD] paste failed: {exc!r}")
            item = None

        if item is None:
            continue

        try:
            scene.addItem(item)
            new_items.append(item)
        except Exception:
            pass

    return new_items


def _create_item(canvas, data):
    """Создаёт один item по данным из clipboard."""

    if not data:
        return None

    item_type = data.get("type")

    from .cards.text.text_card import TextCard
    from .cards.heading.heading_card import HeadingCard
    from .cards.comment.comment_card import CommentCard
    from .cards.image_text.image_card import ImageTextCard
    from .cards.color.color_item import ColorItem
    from .cards.video.video_text_item import VideoTextItem

    x = data.get("x", 0.0)
    y = data.get("y", 0.0)
    width = data.get("width", 280)
    height = data.get("height", 180)
    color = data.get("color", "#FFFFFF")
    title = data.get("title", "")
    text = data.get("text", "")

    from .canvas.card_ids import generate_card_id

    if item_type == "TextCard":

        item = TextCard(
            title=title,
            text=text,
            x=x,
            y=y,
            width=width,
            height=height,
            color=color,
        )

    elif item_type == "HeadingCard":

        item = HeadingCard(
            title=title,
            text=text,
            x=x,
            y=y,
            width=width,
            height=height,
            color=color,
        )

    elif item_type == "CommentCard":

        item = CommentCard(
            title=title,
            text=text,
            width=width,
            height=height,
            color=color,
        )
        item.setPos(x, y)

    elif item_type == "ImageTextCard":

        item = ImageTextCard(
            title=title,
            text=text,
            x=x,
            y=y,
            width=width,
            height=height,
            color=color,
        )

    elif item_type == "ColorItem":

        item = ColorItem(
            color=color,
            width=width,
            height=height,
        )
        item.setPos(x, y)

    elif item_type == "VideoTextItem":

        video_path = data.get("video_path", "")

        if not video_path:
            return None

        item = VideoTextItem(
            title=title,
            text=text,
            video_path=video_path,
            width=width,
            height=height,
            color=color,
        )
        item.setPos(x, y)

    else:
        return None

    # Новый card_id
    try:
        item.card_id = generate_card_id()
    except Exception:
        pass

    return item
