from PySide6.QtCore import QPointF


RESIZE_HANDLE_SIZE = 18.0


def resize_zone(card, pos):
    """
    Проверяет, находится ли курсор в зоне изменения размера.

    Зона находится в правом нижнем углу карточки.
    """
    rect = card.rect()

    return (
        pos.x() >= rect.right() - RESIZE_HANDLE_SIZE
        and
        pos.y() >= rect.bottom() - RESIZE_HANDLE_SIZE
    )


def start_resize(card, pos):
    """
    Запоминает начальную позицию курсора
    и текущий размер карточки.
    """
    card.resizing = True
    card.resize_start_pos = QPointF(pos)
    card.resize_start_size = (
        card.rect().width(),
        card.rect().height(),
    )


def calculate_resize(card, pos):
    """
    Рассчитывает новый размер карточки
    на основании движения курсора.
    """
    if not card.resizing:
        return None

    start_pos = card.resize_start_pos
    start_width, start_height = card.resize_start_size

    delta_x = pos.x() - start_pos.x()
    delta_y = pos.y() - start_pos.y()

    new_width = start_width + delta_x
    new_height = start_height + delta_y

    return new_width, new_height


def finish_resize(card):
    """
    Завершает изменение размера карточки.
    """
    card.resizing = False
    card.resize_start_pos = None
    card.resize_start_size = None