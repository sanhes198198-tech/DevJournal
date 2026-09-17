from PySide6.QtGui import QColor


class ArrowStyle:
    """
    Общие визуальные настройки стрелок.

    Здесь хранятся только параметры внешнего вида.
    Логика геометрии и поведения стрелки находится
    в отдельных модулях.
    """

    NORMAL_COLOR = QColor("#7A7A7A")

    SELECTED_COLOR = QColor("#4F7CFF")

    NORMAL_WIDTH = 1.5

    SELECTED_WIDTH = 2.0