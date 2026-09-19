"""
ReferenceImageItem — картинка-подложка на сцене.

Наследуемся от QGraphicsObject (НЕ от QGraphicsPixmapItem):
только QObject-потомки в Qt могут иметь сигналы.

paint / boundingRect реализованы вручную поверх QPixmap.

ZValue = -100 (под узлами и рёбрами).
Позиция и масштаб — в МЕТРАХ. pixels_per_meter задаёт масштаб:
ширина картинки в метрах = pixmap.width() / pixels_per_meter.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject


class ReferenceImageItem(QGraphicsObject):
    """Подложка под контур."""

    # (x, y) в метрах при перемещении мышью
    position_changed = Signal(float, float)

    Z_VALUE = -100.0

    def __init__(
        self,
        pixmap: QPixmap,
        pixels_per_meter: float = 50.0,
        parent=None,
    ):
        super().__init__(parent)

        self._pixmap = pixmap
        self._ppm = max(0.001, float(pixels_per_meter))
        self._suppress_move = False

        self.setZValue(self.Z_VALUE)
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True,
        )
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True,
        )
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True,
        )

        self.setScale(1.0 / self._ppm)

    # ------------------------------------------------------------

    def boundingRect(self) -> QRectF:
        return QRectF(
            0.0, 0.0,
            float(self._pixmap.width()),
            float(self._pixmap.height()),
        )

    def paint(self, painter, option, widget=None) -> None:
        painter.drawPixmap(0, 0, self._pixmap)

    # ------------------------------------------------------------

    def pixels_per_meter(self) -> float:
        return self._ppm

    def set_pixels_per_meter(self, ppm: float) -> None:
        self._ppm = max(0.001, float(ppm))
        self.setScale(1.0 / self._ppm)

    def set_interactive(self, enabled: bool) -> None:
        """Включить / выключить перетаскивание мышью.

        В draw-режиме editor отключает interaction, чтобы клики
        уходили в сцену, а не в картинку.
        """
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable, enabled,
        )
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, enabled,
        )
        if enabled:
            self.setAcceptedMouseButtons(
                Qt.MouseButton.LeftButton,
            )
        else:
            self.setAcceptedMouseButtons(
                Qt.MouseButton.NoButton,
            )

    # ------------------------------------------------------------

    def itemChange(self, change, value):
        if (
            change
            == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged
            and not self._suppress_move
        ):
            self.position_changed.emit(value.x(), value.y())
        return super().itemChange(change, value)
