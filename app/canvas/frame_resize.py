"""
Resize-логика для FrameItem.
"""

from PySide6.QtCore import QPointF, QRectF


HANDLE_RADIUS = 8.0

MIN_WIDTH = 100.0
MIN_HEIGHT = 80.0

AUTOSIZE_PADDING = 24.0


def resize_zone(frame, pos):
    if frame is None or pos is None:
        return None

    try:
        rect = frame.rect()

        x = pos.x()
        y = pos.y()

        left = rect.left()
        right = rect.right()
        top = rect.top()
        bottom = rect.bottom()

        r = HANDLE_RADIUS

        near_left = abs(x - left) <= r
        near_right = abs(x - right) <= r
        near_top = abs(y - top) <= r
        near_bottom = abs(y - bottom) <= r

        if near_right and near_bottom:
            return "br"
        if near_left and near_bottom:
            return "bl"
        if near_right and near_top:
            return "tr"
        if near_left and near_top:
            return "tl"

        if near_right:
            return "r"
        if near_left:
            return "l"
        if near_bottom:
            return "b"
        if near_top:
            return "t"

    except Exception:
        return None

    return None


def cursor_for_zone(zone):
    mapping = {
        "br": "SizeFDiagCursor",
        "tl": "SizeFDiagCursor",
        "bl": "SizeBDiagCursor",
        "tr": "SizeBDiagCursor",
        "r": "SizeHorCursor",
        "l": "SizeHorCursor",
        "b": "SizeVerCursor",
        "t": "SizeVerCursor",
    }

    return mapping.get(zone)


def start_resize(frame, pos):
    if frame is None or pos is None:
        return

    try:
        zone = resize_zone(frame, pos)

        if zone is None:
            return

        rect = frame.rect()

        frame.resizing = True
        frame.resize_zone_name = zone
        frame.resize_start_pos = QPointF(pos)
        frame.resize_start_rect = (
            rect.left(),
            rect.top(),
            rect.width(),
            rect.height(),
        )
        frame.resize_start_frame_pos = QPointF(frame.pos())

    except Exception:
        frame.resizing = False


def calculate_resize(frame, pos):
    if frame is None or pos is None:
        return None

    if not getattr(frame, "resizing", False):
        return None

    try:
        zone = frame.resize_zone_name
        start_left, start_top, start_w, start_h = frame.resize_start_rect

        dx = pos.x() - frame.resize_start_pos.x()
        dy = pos.y() - frame.resize_start_pos.y()

        new_left = start_left
        new_top = start_top
        new_w = start_w
        new_h = start_h

        if "r" in zone:
            new_w = start_w + dx

        if "l" in zone:
            new_w = start_w - dx
            new_left = start_left + dx

        if "b" in zone:
            new_h = start_h + dy

        if "t" in zone:
            new_h = start_h - dy
            new_top = start_top + dy

        if new_w < MIN_WIDTH:
            if "l" in zone:
                new_left = start_left + (start_w - MIN_WIDTH)
            new_w = MIN_WIDTH

        if new_h < MIN_HEIGHT:
            if "t" in zone:
                new_top = start_top + (start_h - MIN_HEIGHT)
            new_h = MIN_HEIGHT

        return (
            new_left,
            new_top,
            new_w,
            new_h,
        )

    except Exception:
        return None


def apply_resize(frame, pos):
    if frame is None or pos is None:
        return

    result = calculate_resize(frame, pos)

    if result is None:
        return

    new_left, new_top, new_w, new_h = result

    try:
        frame.prepareGeometryChange()

        frame.setRect(
            new_left,
            new_top,
            new_w,
            new_h,
        )

        frame.update()

    except Exception:
        pass


def finish_resize(frame):
    if frame is None:
        return

    try:
        rect = frame.rect()

        current_pos = frame.pos()

        new_pos_x = current_pos.x() + rect.left()
        new_pos_y = current_pos.y() + rect.top()

        frame.prepareGeometryChange()

        frame.setRect(
            0.0,
            0.0,
            rect.width(),
            rect.height(),
        )

        frame.setPos(
            new_pos_x,
            new_pos_y,
        )

        frame.update()

    except Exception:
        pass

    try:
        frame.resizing = False
        frame.resize_zone_name = None
        frame.resize_start_pos = None
        frame.resize_start_rect = None
        frame.resize_start_frame_pos = None

    except Exception:
        pass


# ============================================================
# AUTOSIZE
# ============================================================

def _member_scene_rect(member):
    """
    Универсально получает bbox объекта в координатах сцены.

    Пробует несколько способов, чтобы работать
    с любым типом карточки.
    """

    if member is None:
        return None

    # Способ 1: sceneBoundingRect
    try:
        rect = member.sceneBoundingRect()

        if rect is not None and rect.width() > 0 and rect.height() > 0:
            return rect
    except Exception:
        pass

    # Способ 2: boundingRect + mapToScene
    try:
        local_rect = member.boundingRect()

        if local_rect is not None and local_rect.width() > 0:
            scene_poly = member.mapToScene(local_rect)

            return scene_poly.boundingRect()
    except Exception:
        pass

    # Способ 3: rect + mapToScene
    try:
        local_rect = member.rect()

        if local_rect is not None and local_rect.width() > 0:
            scene_poly = member.mapToScene(local_rect)

            return scene_poly.boundingRect()
    except Exception:
        pass

    # Способ 4: pos + item_width/item_height
    try:
        x = member.pos().x()
        y = member.pos().y()

        w = getattr(member, "item_width", None)
        h = getattr(member, "item_height", None)

        if w is None or h is None:
            w = getattr(member, "WIDTH", None)
            h = getattr(member, "HEIGHT", None)

        if w and h:
            return QRectF(x, y, float(w), float(h))
    except Exception:
        pass

    return None


def autosize_to_members(frame):
    """
    Подгоняет размер и позицию рамки под её содержимое.

    Работает с любыми типами карточек.
    """

    if frame is None:
        return False

    members = getattr(frame, "_members", None)

    if not members:
        return False

    left = None
    top = None
    right = None
    bottom = None

    for member in members:

        rect = _member_scene_rect(member)

        if rect is None:
            continue

        m_left = rect.left()
        m_top = rect.top()
        m_right = rect.right()
        m_bottom = rect.bottom()

        if left is None or m_left < left:
            left = m_left

        if top is None or m_top < top:
            top = m_top

        if right is None or m_right > right:
            right = m_right

        if bottom is None or m_bottom > bottom:
            bottom = m_bottom

    if left is None:
        return False

    new_left = left - AUTOSIZE_PADDING
    new_top = top - AUTOSIZE_PADDING
    new_w = (right - left) + AUTOSIZE_PADDING * 2.0
    new_h = (bottom - top) + AUTOSIZE_PADDING * 2.0

    if new_w < MIN_WIDTH:
        new_w = MIN_WIDTH

    if new_h < MIN_HEIGHT:
        new_h = MIN_HEIGHT

    try:
        frame.prepareGeometryChange()

        frame.setRect(
            0.0,
            0.0,
            new_w,
            new_h,
        )

        frame.setPos(
            new_left,
            new_top,
        )

        frame.update()

    except Exception:
        return False

    return True