"""
Containment logic for frames.
"""

from .frame_item import FrameItem


CONTAINMENT_THRESHOLD = 0.5   # центр внутри -> 1.0, иначе 0.0


# ============================================================
# INTERNAL ITEM FILTER
# ============================================================

# Internal card elements (text, background, video preview) plus
# the frame overlay. These must NOT be attached to a frame -
# their "owner" is the parent card, not the frame.
INTERNAL_TYPE_NAMES = frozenset((
    "EditableText",
    "CardTextItem",
    "QGraphicsRectItem",
    "QGraphicsPixmapItem",
    "QGraphicsTextItem",
    "FrameOverlay",
))


def _is_internal_item(item):
    """
    True if item is an internal element of a card (or the overlay).

    Such items are not taken into account for containment.
    """

    if item is None:
        return True

    try:
        name = type(item).__name__
    except Exception:
        return True

    return name in INTERNAL_TYPE_NAMES


# ============================================================
# HELPERS
# ============================================================

def _scene_rect(item):
    try:
        return item.sceneBoundingRect()
    except Exception:
        return None


def _overlap_ratio(item_rect, frame_rect):
    """
    Возвращает 1.0, если ЦЕНТР элемента внутри рамки, иначе 0.0.

    Это предсказуемое правило: элемент становится членом рамки
    только когда его центр попадает внутрь рамки.
    Никаких "наполовину зашёл — уже член".
    """

    if item_rect is None or frame_rect is None:
        return 0.0

    center = item_rect.center()

    if frame_rect.contains(center):
        return 1.0

    return 0.0


# ============================================================
# FIND FRAME
# ============================================================

def find_frame_for_item(item, scene):
    if item is None or scene is None:
        return None

    if isinstance(item, FrameItem):
        return None

    if _is_internal_item(item):
        return None

    item_rect = _scene_rect(item)

    if item_rect is None:
        return None

    best_frame = None
    best_ratio = 0.0

    try:
        scene_items = scene.items()
    except Exception:
        return None

    frames_count = 0

    for obj in scene_items:
        if not isinstance(obj, FrameItem):
            continue

        if obj is item:
            continue

        frames_count += 1

        # Используем визуальный прямоугольник рамки (rect()),
        # а не sceneBoundingRect() — чтобы не захватить лишнее.
        try:
            frame_rect = obj.mapToScene(obj.rect()).boundingRect()
        except Exception:
            frame_rect = _scene_rect(obj)

        ratio = _overlap_ratio(item_rect, frame_rect)

        if ratio >= CONTAINMENT_THRESHOLD and ratio > best_ratio:
            best_ratio = ratio
            best_frame = obj

    try:
        print(
            f"[FIND_FRAME] item={type(item).__name__} "
            f"scene_items={len(scene_items)} "
            f"frames_on_scene={frames_count} "
            f"best_frame={id(best_frame) if best_frame else None} "
            f"ratio={best_ratio:.2f}"
        )
    except Exception:
        pass

    return best_frame


# ============================================================
# UPDATE MEMBERSHIP
# ============================================================

def update_item_membership(item, scene):
    if item is None or scene is None:
        return None

    if isinstance(item, FrameItem):
        return None

    if _is_internal_item(item):
        return None

    new_frame = find_frame_for_item(item, scene)

    old_frame = getattr(item, "_frame", None)

    if new_frame is old_frame:
        return new_frame

    try:
        print(
            f"[MEMBERSHIP] CHANGE item={type(item).__name__} "
            f"id={id(item)} "
            f"old={id(old_frame) if old_frame else None} "
            f"new={id(new_frame) if new_frame else None}"
        )
    except Exception:
        pass

    # Detach from old frame
    if old_frame is not None:
        try:
            members = getattr(old_frame, "_members", None)

            if members is not None and item in members:
                members.remove(item)
        except Exception:
            pass

    # Attach to new frame
    if new_frame is not None:
        try:
            members = getattr(new_frame, "_members", None)

            if members is None:
                members = []
                new_frame._members = members

            if item not in members:
                members.append(item)
        except Exception:
            pass

    try:
        item._frame = new_frame
    except Exception:
        pass

    return new_frame


# ============================================================
# UPDATE ALL
# ============================================================

def update_all_memberships(scene):
    if scene is None:
        return

    try:
        items = scene.items()
    except Exception:
        return

    # 1. Очищаем _members у ВСЕХ рамок — чтобы не осталось
    #    старых членов от прошлой геометрии.
    for obj in items:
        if isinstance(obj, FrameItem):
            try:
                obj._members = []
            except Exception:
                pass

    # 2. Обнуляем _frame у всех карточек.
    for item in items:
        if isinstance(item, FrameItem):
            continue

        if _is_internal_item(item):
            continue

        try:
            item._frame = None
        except Exception:
            pass

    # 3. Пересчитываем membership с нуля.
    for item in items:
        if isinstance(item, FrameItem):
            continue

        if _is_internal_item(item):
            continue

        try:
            update_item_membership(item, scene)
        except Exception:
            continue


# ============================================================
# DETACH ALL
# ============================================================

def detach_all_members(frame):
    if frame is None:
        return

    members = getattr(frame, "_members", None)

    if not members:
        return

    for member in list(members):
        try:
            if getattr(member, "_frame", None) is frame:
                member._frame = None
        except Exception:
            pass

    try:
        members.clear()
    except Exception:
        pass