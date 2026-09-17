"""
Connection points for cards.

4 точки — по центру каждой стороны:
    top, right, bottom, left

Все точки одного типа. При наведении на карточку — появляются.
Ближайшая к курсору — подсвечивается.

Логика полностью изолирована, чтобы не путать с resize.
"""

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QBrush, QPen


CONNECTION_RADIUS = 5.0

CONNECTION_HOVER_MARGIN = 6.0

COLOR_NORMAL = QColor("#8A8A8A")
COLOR_HOVERED = QColor("#4A90E2")
COLOR_BORDER = QColor("#FFFFFF")

POINT_TOP = 0
POINT_RIGHT = 1
POINT_BOTTOM = 2
POINT_LEFT = 3


def connection_points(card):
    """
    Возвращает список из 4 точек подключения в локальных
    координатах карточки. Порядок: top, right, bottom, left.
    """

    rect = card.rect()

    left = rect.left()
    right = rect.right()
    top = rect.top()
    bottom = rect.bottom()

    cx = (left + right) / 2.0
    cy = (top + bottom) / 2.0

    return [
        QPointF(cx, top),
        QPointF(right, cy),
        QPointF(cx, bottom),
        QPointF(left, cy),
    ]


def connection_point(card):
    """
    Старое API — возвращает одну точку (правый центр).
    Используется в arrow_item.py и routed_arrow.py.
    """

    rect = card.rect()

    return QPointF(
        rect.right(),
        (rect.top() + rect.bottom()) / 2.0,
    )


def has_connection_point(card):
    """
    Может ли карточка иметь точки подключения.
    """

    return card.card_type != "comment"


def nearest_point_index(card, pos):
    """
    Индекс ближайшей точки к pos или None.
    """

    if not has_connection_point(card):
        return None

    points = connection_points(card)

    if not points:
        return None

    radius = CONNECTION_RADIUS + CONNECTION_HOVER_MARGIN
    radius_squared = radius * radius

    best_index = None
    best_distance = radius_squared

    for i, point in enumerate(points):

        dx = pos.x() - point.x()
        dy = pos.y() - point.y()

        distance_squared = dx * dx + dy * dy

        if distance_squared <= best_distance:
            best_distance = distance_squared
            best_index = i

    return best_index


def nearest_point(card, pos):
    """
    Возвращает ближайшую точку (QPointF) или None.
    """

    index = nearest_point_index(card, pos)

    if index is None:
        return None

    return connection_points(card)[index]


def update_connection_hover(card, pos):
    """
    Обновляет состояние hover над точками.
    """

    if not has_connection_point(card):
        card.connection_hovered = False
        card.hover_point_index = None
        return False

    index = nearest_point_index(card, pos)

    card.hover_point_index = index
    card.connection_hovered = index is not None

    return card.connection_hovered


def paint_connection_point(card, painter):
    """
    Рисует 4 точки подключения.
    Точки видны ТОЛЬКО при hover на карточку.
    Ближайшая к курсору — подсвечена синим.
    """

    if not has_connection_point(card):
        return

    if not getattr(card, "connection_hovered", False):
        active = getattr(card, "hover_point_index", None)

        if active is None:
            return

    points = connection_points(card)

    active_index = getattr(card, "hover_point_index", None)

    for i, point in enumerate(points):

        if i == active_index:
            radius = CONNECTION_RADIUS + 2.0

            painter.setPen(QPen(COLOR_BORDER, 2.0))
            painter.setBrush(QBrush(COLOR_HOVERED))
        else:
            radius = CONNECTION_RADIUS

            painter.setPen(QPen(COLOR_BORDER, 1.5))
            painter.setBrush(QBrush(COLOR_NORMAL))

        painter.drawEllipse(point, radius, radius)