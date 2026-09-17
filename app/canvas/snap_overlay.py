"""
Snap overlay - рисует линии-направляющие при перетаскивании карточек.

Показывает вертикальные и горизонтальные линии, которые помогают
выровнять карточки по краям и центрам.
"""

from PySide6.QtCore import Qt, QLineF
from PySide6.QtGui import QColor, QPen, QPainter
from PySide6.QtWidgets import QGraphicsItem


class SnapOverlay(QGraphicsItem):

    Z_VALUE = 100000

    COLOR = QColor("#4F7CFF")

    WIDTH = 1.0

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setZValue(self.Z_VALUE)

        self._vertical_lines = []    # список X координат
        self._horizontal_lines = []  # список Y координат

        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
            False,
        )
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
            False,
        )

    def boundingRect(self):
        """
        Фиксированный прямоугольник — покрывает всю сцену.
        Так Qt гарантированно вызывает paint для любой части сцены.
        """

        from PySide6.QtCore import QRectF

        return QRectF(-50000, -50000, 100000, 100000)

    def paint(self, painter, option, widget=None):
        """
        Рисует сохранённые линии.
        """

        if not self._vertical_lines and not self._horizontal_lines:
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        pen = QPen(self.COLOR, self.WIDTH)
        pen.setCosmetic(True)

        painter.setPen(pen)

        # Большой диапазон — покрывает всю сцену
        MIN = -50000
        MAX = 50000

        # Вертикальные линии (по X)
        for x in self._vertical_lines:
            painter.drawLine(
                QLineF(x, MIN, x, MAX)
            )

        # Горизонтальные линии (по Y)
        for y in self._horizontal_lines:
            painter.drawLine(
                QLineF(MIN, y, MAX, y)
            )

    def set_guides(self, vertical=None, horizontal=None):
        """
        Устанавливает линии-направляющие.

        vertical   - список X координат (в сцене)
        horizontal - список Y координат (в сцене)
        """

        self._vertical_lines = list(vertical or [])
        self._horizontal_lines = list(horizontal or [])

        self.update()

    def clear_guides(self):
        """
        Убирает все линии.
        """

        if not self._vertical_lines and not self._horizontal_lines:
            return

        self._vertical_lines = []
        self._horizontal_lines = []

        self.update()
