"""
Восстановление сохранённой геометрии карточек.

Модуль нужен для того, чтобы после восстановления текста,
HTML и других данных карточка снова получила именно те
размеры, которые были сохранены в board.json.

Это особенно важно для connection_point(), поскольку
точка подключения стрелки зависит от текущего rect() карточки.
"""


def restore_card_geometry(card, width, height):
    """
    Восстанавливает сохранённые размеры карточки.

    Функция вызывается ПОСЛЕ восстановления содержимого карточки,
    чтобы автоматический пересчёт высоты текста больше не мог
    изменить сохранённую геометрию перед восстановлением стрелок.
    """

    if card is None:
        return

    try:
        width = float(width)
        height = float(height)
    except (TypeError, ValueError):
        return

    if width <= 0 or height <= 0:
        return

    try:
        current_rect = card.rect()

        if (
            abs(current_rect.width() - width) < 0.01
            and
            abs(current_rect.height() - height) < 0.01
        ):
            return

        card.prepareGeometryChange()

        card.setRect(
            0,
            0,
            width,
            height,
        )

        card.update()

    except Exception:
        pass


def restore_card_geometry_from_data(card, item_data):
    """
    Восстанавливает размеры карточки непосредственно
    из словаря данных board.json.
    """

    if not isinstance(item_data, dict):
        return

    restore_card_geometry(
        card,
        item_data.get("width"),
        item_data.get("height"),
    )