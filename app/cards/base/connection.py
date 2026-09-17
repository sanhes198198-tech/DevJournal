from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QBrush, QPen


CONNECTION_RADIUS = 5.0


def has_connection_point(card):
    """
    Проверяет, должна ли карточка иметь точку подключения.

    Комментарий является единственным типом карточки
    без точки подключения.
    """
    return card.card_type != "comment"


def connection_point(card):
    """
    Возвращает координаты точки подключения.

    Точка находится в правом нижнем углу карточки.
    """
    rect = card.rect()

    return QPointF(
        rect.right(),
        rect.bottom(),
    )


def update_connection_hover(card, pos):
    """
    Проверяет, находится ли курсор над точкой подключения.
    """
    if not has_connection_point(card):
        card.connection_hovered = False
        return False

    point = connection_point(card)

    distance_x = pos.x() - point.x()
    distance_y = pos.y() - point.y()

    distance_squared = (
        distance_x * distance_x
        + distance_y * distance_y
    )

    radius = CONNECTION_RADIUS + 4.0

    card.connection_hovered = (
        distance_squared <= radius * radius
    )

    return card.connection_hovered


def paint_connection_point(card, painter):
    """
    Рисует точку подключения карточки.
    """
    if not has_connection_point(card):
        return

    point = connection_point(card)

    if card.connection_hovered:
        radius = CONNECTION_RADIUS + 2.0

        painter.setPen(
            QPen(
                QColor("#FFFFFF"),
                2.0,
            )
        )

        painter.setBrush(
            QBrush(
                QColor("#4A90E2"),
            )
        )
    else:
        radius = CONNECTION_RADIUS

        painter.setPen(
            QPen(
                QColor("#FFFFFF"),
                1.5,
            )
        )

        painter.setBrush(
            QBrush(
                QColor("#777777"),
            )
        )

    painter.drawEllipse(
        point,
        radius,
        radius,
    )