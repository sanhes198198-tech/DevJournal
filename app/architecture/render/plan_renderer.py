"""
PlanRenderer — рисование плана в стиле архитектурного чертежа.

ТОЛЬКО КОНТУРЫ, без заливок.
Белый фон, чёрные тонкие линии, как в реальных чертежах.

Шрифты фиксированные (DirectWrite не любит микроскопические).
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPen


class PlanRenderer:
    """Рендер плана (вид сверху), чертёжный стиль."""

    # Цвета — контурный стиль (белый фон, чёрные линии)
    ROOM_LINE = QColor("#1A1A1A")           # почти чёрная
    ROOM_LINE_SELECTED = QColor("#0055CC")  # синяя при выделении

    TEXT_NAME = QColor("#000000")           # чёрный
    TEXT_SIZE = QColor("#555555")           # серый
    TEXT_DIM = QColor("#888888")            # светлее

    # Толщины (в пикселях — cosmetic, не зависит от zoom)
    LINE_WIDTH = 1.2
    LINE_WIDTH_SELECTED = 2.0

    # Размеры шрифта (фиксированные)
    NAME_FONT_SIZE = 0.7
    SIZE_FONT_SIZE = 0.45

    # Порог для вертикального текста
    VERTICAL_THRESHOLD = 1.5

    # ------------------------------------------------------------------

    @staticmethod
    def draw_room(
        painter,
        rect: QRectF,
        room,
        selected: bool = False,
        ppm: float = 50.0,
    ) -> None:
        """Комната — прямоугольник контуром, без заливки."""
        painter.save()
        painter.setRenderHint(painter.RenderHint.Antialiasing, True)

        color = (
            PlanRenderer.ROOM_LINE_SELECTED
            if selected
            else PlanRenderer.ROOM_LINE
        )
        width = (
            PlanRenderer.LINE_WIDTH_SELECTED
            if selected
            else PlanRenderer.LINE_WIDTH
        )

        pen = QPen(color, width)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.drawRect(rect)

        # Тексты — только если места достаточно
        px_w = rect.width() * ppm
        px_h = rect.height() * ppm

        if px_w > 80 and px_h > 60:
            PlanRenderer._draw_room_labels(painter, rect, room)

        painter.restore()

    # ------------------------------------------------------------------
    # TEXT
    # ------------------------------------------------------------------

    @staticmethod
    def _draw_room_labels(painter, rect: QRectF, room) -> None:
        """Имя + размеры + высота. Ориентация зависит от пропорций."""
        painter.save()
        painter.setClipRect(rect)

        is_vertical = rect.height() > rect.width() * PlanRenderer.VERTICAL_THRESHOLD

        if is_vertical:
            painter.translate(rect.center())
            painter.rotate(-90)
            w = rect.height()
            h = rect.width()
            local = QRectF(-w / 2.0, -h / 2.0, w, h)
        else:
            local = rect

        pad = 0.2
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

        name_rect = QRectF(
            local.left() + pad,
            cy - local.height() * 0.22,
            max_w,
            local.height() * 0.25,
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
            size_text, Qt.TextElideMode.ElideRight, max_w
        )

        size_rect = QRectF(
            local.left() + pad,
            cy + local.height() * 0.05,
            max_w,
            local.height() * 0.18,
        )
        painter.drawText(
            size_rect,
            Qt.AlignmentFlag.AlignCenter,
            size_text,
        )

        # --- Высота ---
        h_font = QFont()
        h_font.setPointSizeF(PlanRenderer.SIZE_FONT_SIZE * 0.9)
        painter.setFont(h_font)
        painter.setPen(PlanRenderer.TEXT_DIM)

        h_text = f"h = {room.height:.1f} m"
        fm3 = QFontMetricsF(h_font)
        h_text = fm3.elidedText(
            h_text, Qt.TextElideMode.ElideRight, max_w
        )

        h_rect = QRectF(
            local.left() + pad,
            cy + local.height() * 0.25,
            max_w,
            local.height() * 0.16,
        )
        painter.drawText(
            h_rect,
            Qt.AlignmentFlag.AlignCenter,
            h_text,
        )

        painter.restore()
