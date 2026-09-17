from PySide6.QtGui import QColor


class ArrowStyle:
    """
    Общие визуальные настройки стрелок.

    Здесь хранятся только параметры внешнего вида.
    Логика геометрии и поведения стрелки находится
    в отдельных модулях.
    """

    NORMAL_COLOR = QColor("#000000")

    SELECTED_COLOR = QColor("#000000")

    NORMAL_WIDTH = 2.0

    SELECTED_WIDTH = 2.5