"""
Frame persistence for board.json.

Symmetric to arrow_persistence.py.
"""

from .frame_item import FrameItem
from .frame_title import get_title_html, set_title_html


DEFAULT_FRAME_COLOR = "#B0B0B0"


def serialize_frame(frame):
    if not isinstance(frame, FrameItem):
        return None

    try:
        rect = frame.rect()
    except Exception:
        return None

    member_ids = []

    for member in (getattr(frame, "_members", None) or []):
        try:
            card_id = getattr(member, "card_id", None)
        except Exception:
            card_id = None

        if card_id is None:
            continue

        value = str(card_id).strip()

        if value:
            member_ids.append(value)

    # Save title HTML (font, size, bold, italic).
    title_html = ""

    try:
        title_item = getattr(frame, "title_item", None)

        print(
            f"[PERSIST] serialize_frame: "
            f"title_item={title_item} "
            f"is_none={title_item is None}"
        )

        title_html = get_title_html(title_item)

        print(
            f"[PERSIST] title_html len={len(title_html)}"
        )

    except Exception as exc:
        print(f"[PERSIST] serialize_frame error: {exc!r}")
        title_html = ""

    return {
        "type": "frame",
        "frame_id": getattr(frame, "frame_id", None),
        "title": getattr(frame, "title", ""),
        "title_html": title_html,
        "frame_color": getattr(
            frame,
            "frame_color",
            DEFAULT_FRAME_COLOR,
        ),
        "frame_fill": getattr(
            frame,
            "frame_fill",
            "transparent",
        ),
        "locked": bool(getattr(frame, "locked", False)),
        "x": frame.pos().x(),
        "y": frame.pos().y(),
        "width": rect.width(),
        "height": rect.height(),
        "members": member_ids,
    }


def collect_frames(scene):
    if scene is None:
        return []

    result = []

    try:
        items = scene.items()
    except Exception:
        return result

    for item in items:
        if not isinstance(item, FrameItem):
            continue

        data = serialize_frame(item)

        if data is not None:
            result.append(data)

    return result


def restore_frames(canvas, frames_data, item_by_id):
    if not isinstance(frames_data, list):
        return []

    restored = []

    for frame_data in frames_data:
        frame = _restore_one(canvas, frame_data, item_by_id)

        if frame is not None:
            restored.append(frame)

    return restored


def _restore_one(canvas, frame_data, item_by_id):
    if not isinstance(frame_data, dict):
        return None

    frame_id = frame_data.get("frame_id")

    if not frame_id:
        return None

    saved_color = frame_data.get(
        "frame_color",
        DEFAULT_FRAME_COLOR,
    )

    saved_fill = frame_data.get("frame_fill", "transparent")

    saved_locked = bool(frame_data.get("locked", False))

    try:
        frame = FrameItem(
            x=0.0,
            y=0.0,
            width=frame_data.get(
                "width",
                FrameItem.DEFAULT_WIDTH,
            ),
            height=frame_data.get(
                "height",
                FrameItem.DEFAULT_HEIGHT,
            ),
            title=frame_data.get(
                "title",
                "\u0420\u0430\u043c\u043a\u0430",
            ),
            frame_id=frame_id,
            frame_color=saved_color,
            frame_fill=saved_fill,
            locked=saved_locked,
        )
    except Exception:
        return None

    try:
        frame.setPos(
            frame_data.get("x", 0.0),
            frame_data.get("y", 0.0),
        )
    except Exception:
        pass

    # Restore title HTML (font, size, bold, italic).
    try:
        saved_html = frame_data.get("title_html", "")

        if saved_html:
            set_title_html(frame.title_item, saved_html)
    except Exception:
        pass

    try:
        canvas.scene.addItem(frame)
    except Exception:
        return None

    members = []

    for card_id in (frame_data.get("members", []) or []):
        if not isinstance(card_id, str):
            continue

        member = item_by_id.get(card_id.strip())

        if member is None:
            continue

        try:
            member._frame = frame
        except Exception:
            pass

        members.append(member)

    try:
        frame._members = members
    except Exception:
        pass

    return frame