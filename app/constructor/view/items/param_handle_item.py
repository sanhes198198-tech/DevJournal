"""
ParamHandleItem — on-canvas слайдер для параметра sub-ассета.

При выделении ComponentItem создаёт два слайдера:
  - вертикальный (справа) для height
  - горизонтальный (снизу) для width

Перетаскивание ручки меняет override параметра в реальном времени.
Без текста, без children — только капсула и ручка.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject


CAPSULE_THICK = 0.28
CAPSULE_LENGTH = 2.4
KNOB_RADIUS = 0.18
VALUE_RANGE = 4.0

CAPSULE_LINE_COLOR = QColor("#8892A0")
CAPSULE_LINE_WIDTH = 0.015
CAPSULE_BG_COLOR = QColor(255, 255, 255, 200)
KNOB_LINE_COLOR = QColor("#5A6270")
KNOB_LINE_WIDTH = 0.02
KNOB_BG_COLOR = QColor("#FFFFFF")
KNOB_DOT_COLOR = QColor("#5A6270")


class ParamHandleItem(QGraphicsObject):
    """Слайдер-капсула для параметра."""

    value_changed = Signal(str, float)

    def __init__(
        self,
        param_name: str,
        orientation: str,
        base_value: float,
        current_value: float,
        parent=None,
    ):
        super().__init__(parent)
        self._param_name = param_name
        self._orientation = orientation
        self._base_value = float(base_value)
        self._current_value = float(current_value)

        self._min_value = self._base_value - VALUE_RANGE
        self._max_value = self._base_value + VALUE_RANGE

        self._dragging = False

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, False)
        self.setZValue(500.0)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

    @property
    def param_name(self) -> str:
        return self._param_name

    def set_current_value(self, value: float) -> None:
        self._current_value = float(value)
        self.update()

    def boundingRect(self) -> QRectF:
        if self._orientation == "v":
            r = QRectF(
                -CAPSULE_THICK / 2, -CAPSULE_LENGTH / 2,
                CAPSULE_THICK, CAPSULE_LENGTH,
            )
        else:
            r = QRectF(
                -CAPSULE_LENGTH / 2, -CAPSULE_THICK / 2,
                CAPSULE_LENGTH, CAPSULE_THICK,
            )
        return r.adjusted(-0.5, -0.5, 0.5, 0.5)

    def _knob_pos(self) -> float:
        t = (self._current_value - self._min_value) / (
            self._max_value - self._min_value
        )
        t = max(0.0, min(1.0, t))
        if self._orientation == "v":
            return CAPSULE_LENGTH / 2 - t * CAPSULE_LENGTH
        else:
            return -CAPSULE_LENGTH / 2 + t * CAPSULE_LENGTH

    def _capsule_path(self) -> QPainterPath:
        path = QPainterPath()
        if self._orientation == "v":
            rect = QRectF(
                -CAPSULE_THICK / 2, -CAPSULE_LENGTH / 2,
                CAPSULE_THICK, CAPSULE_LENGTH,
            )
        else:
            rect = QRectF(
                -CAPSULE_LENGTH / 2, -CAPSULE_THICK / 2,
                CAPSULE_LENGTH, CAPSULE_THICK,
            )
        path.addRoundedRect(rect, CAPSULE_THICK / 2, CAPSULE_THICK / 2)
        return path

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Капсула
        pen = QPen(CAPSULE_LINE_COLOR, CAPSULE_LINE_WIDTH)
        painter.setPen(pen)
        painter.setBrush(QBrush(CAPSULE_BG_COLOR))
        painter.drawPath(self._capsule_path())

        # Ручка
        knob = self._knob_pos()
        if self._orientation == "v":
            center = QPointF(0.0, knob)
        else:
            center = QPointF(knob, 0.0)

        knob_pen = QPen(KNOB_LINE_COLOR, KNOB_LINE_WIDTH)
        painter.setPen(knob_pen)
        painter.setBrush(QBrush(KNOB_BG_COLOR))
        painter.drawEllipse(center, KNOB_RADIUS, KNOB_RADIUS)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(KNOB_DOT_COLOR))
        painter.drawEllipse(center, KNOB_RADIUS * 0.28, KNOB_RADIUS * 0.28)

    def _knob_hit(self, pos: QPointF) -> bool:
        knob = self._knob_pos()
        if self._orientation == "v":
            return abs(pos.y() - knob) <= KNOB_RADIUS * 2.2
        else:
            return abs(pos.x() - knob) <= KNOB_RADIUS * 2.2

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        if not self._knob_hit(event.pos()):
            event.ignore()
            return
        self._dragging = True
        event.accept()

    def mouseMoveEvent(self, event):
        if not self._dragging:
            event.ignore()
            return
        pos = event.pos()
        if self._orientation == "v":
            t = (CAPSULE_LENGTH / 2 - pos.y()) / CAPSULE_LENGTH
        else:
            t = (pos.x() + CAPSULE_LENGTH / 2) / CAPSULE_LENGTH
        t = max(0.0, min(1.0, t))
        new_value = self._min_value + t * (
            self._max_value - self._min_value
        )
        self._current_value = new_value
        self.update()
        self.value_changed.emit(self._param_name, new_value)
        event.accept()

    def mouseReleaseEvent(self, event):
        if not self._dragging:
            event.ignore()
            return
        self._dragging = False
        event.accept()
