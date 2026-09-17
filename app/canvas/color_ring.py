"""
Цветовое кольцо (Hue) + SV-квадрат.

Используется для выбора произвольного цвета
в цветовой карточке (ColorItem).
"""

import math

from PySide6.QtCore import (
    Qt,
    QPoint,
    QPointF,
    QRectF,
    QTimer,
)
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPen,
    QBrush,
    QConicalGradient,
    QLinearGradient,
    QPainterPath,
    QCursor,
)
from PySide6.QtWidgets import (
    QWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QApplication,
)


# =========================================================
# Виджет: Hue-кольцо + SV-квадрат
# =========================================================

class ColorWheel(QWidget):
    """
    Hue-кольцо с SV-квадратом внутри.

    - Клик по кольцу → меняет hue.
    - Клик по SV-квадрату → меняет saturation / value.
    """

    RING_OUTER = 220
    RING_INNER = 170
    SV_SIZE = 120

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedSize(
            self.RING_OUTER + 10,
            self.RING_OUTER + 10,
        )

        self.hue = 0
        self.saturation = 255
        self.value = 255

        self.dragging = None

        self._update_from_hsv()

    # =====================================================
    # HSV
    # =====================================================

    def _update_from_hsv(self):

        self.current_color = QColor.fromHsv(
            self.hue,
            self.saturation,
            self.value,
        )

    def set_hsv_from_color(self, color):

        if not isinstance(color, QColor):
            color = QColor(color)

        if not color.isValid():
            return

        h, s, v, _ = color.getHsv()

        if h < 0:
            h = 0

        self.hue = h
        self.saturation = s
        self.value = v

        self._update_from_hsv()
        self.update()

    def get_color(self):
        return QColor(self.current_color)

    # =====================================================
    # Геометрия
    # =====================================================

    def _center(self):
        """
        Возвращает QPointF — центр виджета.
        """
        return QPointF(
            self.width() / 2,
            self.height() / 2,
        )

    def _ring_outer_radius(self):
        return self.RING_OUTER / 2

    def _ring_inner_radius(self):
        return self.RING_INNER / 2

    def _sv_rect(self):
        """
        Возвращает QRectF — область SV-квадрата.
        """
        size = self.SV_SIZE

        center = self._center()

        cx = center.x()
        cy = center.y()

        return QRectF(
            cx - size / 2,
            cy - size / 2,
            size,
            size,
        )

    # =====================================================
    # PAINT
    # =====================================================

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        try:

            center = self._center()
            outer_r = self._ring_outer_radius()
            inner_r = self._ring_inner_radius()

            # ---------------------------------------------
            # 1. Кольцо Hue
            # ---------------------------------------------

            gradient = QConicalGradient(center, -90)

            for i in range(0, 361, 1):
                h = i % 360
                gradient.setColorAt(
                    i / 360.0,
                    QColor.fromHsv(h, 255, 255),
                )

            path = self._ring_path(center, outer_r, inner_r)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(gradient))
            painter.drawPath(path)

            painter.setPen(QPen(QColor(0, 0, 0, 40), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, outer_r, outer_r)
            painter.drawEllipse(center, inner_r, inner_r)

            # ---------------------------------------------
            # 2. SV-квадрат
            # ---------------------------------------------

            sv_rect = self._sv_rect()

            hue_color = QColor.fromHsv(self.hue, 255, 255)

            grad_h = QLinearGradient(
                sv_rect.topLeft(),
                sv_rect.topRight(),
            )
            grad_h.setColorAt(0.0, QColor(255, 255, 255))
            grad_h.setColorAt(1.0, hue_color)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad_h))
            painter.drawRect(sv_rect)

            grad_v = QLinearGradient(
                sv_rect.topLeft(),
                sv_rect.bottomLeft(),
            )
            grad_v.setColorAt(0.0, QColor(0, 0, 0, 0))
            grad_v.setColorAt(1.0, QColor(0, 0, 0, 255))

            painter.setBrush(QBrush(grad_v))
            painter.drawRect(sv_rect)

            painter.setPen(QPen(QColor(0, 0, 0, 60), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(sv_rect)

            # ---------------------------------------------
            # 3. Маркер на кольце
            # ---------------------------------------------

            angle_rad = math.radians(self.hue - 90)

            ring_mid_r = (outer_r + inner_r) / 2

            mx = center.x() + ring_mid_r * math.cos(angle_rad)
            my = center.y() + ring_mid_r * math.sin(angle_rad)

            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.setBrush(QColor.fromHsv(self.hue, 255, 255))

            painter.drawEllipse(
                QPointF(mx, my),
                (outer_r - inner_r) / 2 - 2,
                (outer_r - inner_r) / 2 - 2,
            )

            # ---------------------------------------------
            # 4. Маркер в SV
            # ---------------------------------------------

            sx = (
                sv_rect.left()
                + (self.saturation / 255.0) * sv_rect.width()
            )

            sy = (
                sv_rect.top()
                + (1 - self.value / 255.0) * sv_rect.height()
            )

            marker_rect = QRectF(
                sx - 7,
                sy - 7,
                14,
                14,
            )

            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(0, 0, 0, 200), 2))
            painter.drawEllipse(marker_rect)

            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawEllipse(
                marker_rect.adjusted(1, 1, -1, -1)
            )

        finally:
            painter.end()

    def _ring_path(self, center, outer_r, inner_r):

        path = QPainterPath()
        path.addEllipse(center, outer_r, outer_r)
        path.addEllipse(center, inner_r, inner_r)
        path.setFillRule(Qt.FillRule.OddEvenFill)

        return path

    # =====================================================
    # MOUSE
    # =====================================================

    def mousePressEvent(self, event):

        if event.button() != Qt.MouseButton.LeftButton:
            return

        pos = event.position()

        sv_rect = self._sv_rect()

        if sv_rect.contains(pos):

            self.dragging = "sv"
            self._update_sv(pos)

        else:

            center = self._center()

            dx = pos.x() - center.x()
            dy = pos.y() - center.y()

            distance = math.sqrt(dx * dx + dy * dy)

            if (
                self._ring_inner_radius()
                <= distance
                <= self._ring_outer_radius() + 4
            ):

                self.dragging = "ring"
                self._update_ring(pos)

    def mouseMoveEvent(self, event):

        if self.dragging == "sv":
            self._update_sv(event.position())

        elif self.dragging == "ring":
            self._update_ring(event.position())

    def mouseReleaseEvent(self, event):

        self.dragging = None

    def _update_sv(self, pos):

        sv_rect = self._sv_rect()

        x = pos.x() - sv_rect.left()
        y = pos.y() - sv_rect.top()

        x = max(0.0, min(x, sv_rect.width()))
        y = max(0.0, min(y, sv_rect.height()))

        s = int((x / sv_rect.width()) * 255)
        v = int((1 - y / sv_rect.height()) * 255)

        self.saturation = max(0, min(255, s))
        self.value = max(0, min(255, v))

        self._update_from_hsv()
        self.update()

    def _update_ring(self, pos):

        center = self._center()

        dx = pos.x() - center.x()
        dy = pos.y() - center.y()

        angle = math.degrees(math.atan2(dy, dx))

        hue = (angle + 90) % 360

        self.hue = int(hue)

        self._update_from_hsv()
        self.update()


# =========================================================
# Пипетка
# =========================================================

class ColorPicker:

    @staticmethod
    def pick_at_cursor():

        screen = QApplication.primaryScreen()

        if screen is None:
            return QColor()

        pos = QCursor.pos()

        pixmap = screen.grabWindow(
            0,
            pos.x(),
            pos.y(),
            1,
            1,
        )

        if pixmap.isNull():
            return QColor()

        image = pixmap.toImage()

        if image.isNull():
            return QColor()

        return QColor(image.pixel(0, 0))


# =========================================================
# Основной попап
# =========================================================

class ColorRingPopup(QWidget):

    def __init__(
        self,
        parent=None,
        initial_color=None,
    ):
        super().__init__(
            parent,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint,
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True,
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_DeleteOnClose,
            True,
        )

        self.setWindowFlag(
            Qt.WindowType.WindowStaysOnTopHint,
            True,
        )

        self.result_color = QColor()

        outer = QFrame(self)
        outer.setObjectName("colorRingFrame")
        outer.setStyleSheet(
            """
            QFrame#colorRingFrame {
                background: #F5F0E8;
                border: 1px solid #E0D9CC;
                border-radius: 10px;
            }

            QPushButton {
                background: #FFFFFF;
                border: 1px solid #DCDCD7;
                border-radius: 6px;
                padding: 4px 10px;
                color: #333333;
                font-size: 12px;
                min-height: 24px;
            }

            QPushButton:hover {
                background: #F1F1EE;
            }
            """
        )

        layout = QVBoxLayout(outer)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.wheel = ColorWheel(outer)
        layout.addWidget(
            self.wheel,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )

        if initial_color is not None:
            self.wheel.set_hsv_from_color(initial_color)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.setSpacing(6)

        self.btn_picker = QPushButton("Пипетка")
        self.btn_picker.setToolTip(
            "Активировать пипетку, затем кликнуть на экране"
        )
        self.btn_picker.clicked.connect(self._activate_picker)

        self.btn_ok = QPushButton("OK")
        self.btn_ok.clicked.connect(self._accept)

        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self._reject)

        bottom.addWidget(self.btn_picker)
        bottom.addStretch()
        bottom.addWidget(self.btn_ok)
        bottom.addWidget(self.btn_cancel)

        layout.addLayout(bottom)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(outer)

        self._picker_active = False
        self._poll_timer = None

        self.adjustSize()

    # =========================================================
    # ПИПЕТКА
    # =========================================================

    def _activate_picker(self):

        QApplication.setOverrideCursor(
            Qt.CursorShape.CrossCursor
        )

        QApplication.processEvents()

        self._picker_active = True

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_picker)
        self._poll_timer.start(50)

    def _poll_picker(self):

        if not self._picker_active:
            return

        if QApplication.mouseButtons() & Qt.MouseButton.LeftButton:

            color = ColorPicker.pick_at_cursor()

            if self._poll_timer is not None:
                self._poll_timer.stop()

            self._picker_active = False

            QApplication.restoreOverrideCursor()

            if color.isValid():
                self.wheel.set_hsv_from_color(color)

    # =========================================================
    # OK / CANCEL
    # =========================================================

    def _accept(self):

        self.result_color = self.wheel.get_color()
        self.close()

    def _reject(self):

        self.result_color = QColor()
        self.close()

    # =========================================================
    # Показ
    # =========================================================

    def show_at(self, global_pos):

        self.adjustSize()
        self.move(global_pos)
        self.show()

    def get_color(self):

        return QColor(self.result_color)