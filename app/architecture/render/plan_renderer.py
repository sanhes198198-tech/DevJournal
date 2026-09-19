"""
PlanRenderer — рисование элементов на плане (вид сверху).

Тупой renderer: получает готовый rect + элемент + флаг selected.
Сам ничего не вычисляет из модели.

Шрифты — фиксированного размера (DirectWrite на Windows не любит
микроскопические размеры).

Ориентация текста автоматическая:
  - широкая комната → текст горизонтально
  - узкая высокая  → текст вертикально (поворот -90°)
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPen


class PlanRenderer:
    """Рендер плана (вид сверху)."""

    # Цвета
    FILL_NORMAL = QColor("#2A3A4A")
    FILL_SELECTED = QColor("#3A5A7A")
    BORDER_NORMAL = QColor("#5A6A7A")
    BORDER_SELECTED = QColor("#7AAAD0")
    TEXT_NAME = QColor("#E5E5E5")
    TEXT_SIZE = QColor("#C5CAD2")

    # Размеры (в scene units = метрах)
    BORDER_WIDTH = 1.5
    BORDER_WIDTH_SELECTED = 2.5

    # Размеры шрифта — ФИКСИРОВАННЫЕ
    NAME_FONT_SIZE = 0.7
    SIZE_FONT_SIZE = 0.45

    # Порог для вертикального текста: depth / width
    VERTICAL_THRESHOLD = 1.5

    # ------------------------------------------------------------------
    # PUBLIC
    # ------------------------------------------------------------------

    @staticmethod
    def draw_room(
        painter,
        rect: QRectF,
        room,
        selected: bool = False,
        ppm: float = 50.0,
    ) -> None:
        """Рисует комнату."""
        painter.save()
        painter.setRenderHint(painter.RenderHint.Antialiasing, True)

        # Заливка
        fill = (
            PlanRenderer.FILL_SELECTED
            if selected
            else PlanRenderer.FILL_NORMAL
        )
        painter.setBrush(fill)

        # Границы
        border = (
            PlanRenderer.BORDER_SELECTED
            if selected
            else PlanRenderer.BORDER_NORMAL
        )
        border_w = (
            PlanRenderer.BORDER_WIDTH_SELECTED
            if selected
            else PlanRenderer.BORDER_WIDTH
        )

        pen = QPen(border, border_w)
        pen.setCosmetic(True)
        painter.setPen(pen)

        painter.drawRect(rect)

        # Тексты — если места достаточно
        px_w = rect.width() * ppm
        px_h = rect.height() * ppm

        if px_w > 80 and px_h > 60:
            PlanRenderer._draw_labels(painter, rect, room)

        painter.restore()

    # ------------------------------------------------------------------
    # TEXT
    # ------------------------------------------------------------------

    @staticmethod
    def _draw_labels(painter, rect: QRectF, room) -> None:
        """Имя + размеры. Ориентация зависит от пропорций."""
        painter.save()
        painter.setClipRect(rect)

        # Определяем ориентацию
        if rect.height() > rect.width() * PlanRenderer.VERTICAL_THRESHOLD:
            # Узкая высокая — вертикально
            painter.translate(rect.center())
            painter.rotate(-90)

            # После поворота система координат повёрнута на 90°.
            # Локальный прямоугольник: центр в (0, 0), ширины поменялись.
            w = rect.height()  # было depth, стало шириной
            h = rect.width()   # было width, стало высотой
            local = QRectF(-w / 2.0, -h / 2.0, w, h)
        else:
            # Широкая — горизонтально
            local = rect

        pad = 0.15
        max_w = local.width() - pad * 2

        if max_w <= 0.2:
            painter.restore()
            return

        cy = local.center().y()

        # --- Имя ---
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSizeF(PlanRenderer.NAME_FONT_SIZE)

        painter.setFont(name_font)
        painter.setPen(PlanRenderer.TEXT_NAME)

        fm = QFontMetricsF(name_font)
        name_text = fm.elidedText(
            room.name or "Комната",
            Qt.TextElideMode.ElideRight,
            max_w,
        )

        name_h = local.height() * 0.25
        name_rect = QRectF(
            local.left() + pad,
            cy - name_h - 0.1,
            max_w,
            name_h,
        )
        painter.drawText(
            name_rect,
            Qt.AlignmentFlag.AlignCenter,
            name_text,
        )

        # --- Размеры ---
        size_font = QFont()
        size_font.setPointSizeF(PlanRenderer.SIZE_FONT_SIZE)

        painter.setFont(size_font)
        painter.setPen(PlanRenderer.TEXT_SIZE)

        size_text = f"{room.width:.1f} x {room.depth:.1f} m"

        fm2 = QFontMetricsF(size_font)
        size_text = fm2.elidedText(
            size_text,
            Qt.TextElideMode.ElideRight,
            max_w,
        )

        size_h = local.height() * 0.2
        size_rect = QRectF(
            local.left() + pad,
            cy + 0.1,
            max_w,
            size_h,
        )
        painter.drawText(
            size_rect,
            Qt.AlignmentFlag.AlignCenter,
            size_text,
        )

        painter.restore()
