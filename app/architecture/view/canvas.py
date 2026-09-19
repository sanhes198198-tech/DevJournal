"""
ArchCanvas — QGraphicsView архитектурного редактора.

Управление:
  - Колесо        → zoom к курсору
  - Shift+drag    → pan
  - Middle drag   → pan
  - Клавиша 0     → reset view
  - Escape        → отмена текущего инструмента

Инструменты (tool):
  - "select"  → обычный режим (выделение, pan)
  - "room"    → drag-to-create комнаты

Координаты: метры. Сцена Y↓, модель Y↑ (конвертация в coords.py).
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QCursor, QPen
from PySide6.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsView,
)

from .scene import ArchScene


# Ограничения zoom (pixels per meter)
PPM_MIN = 0.5
PPM_MAX = 500.0
PPM_DEFAULT = 50.0

# Минимальный размер комнаты при создании (метры)
MIN_CREATE_SIZE = 0.5

# Округление координат при создании (метры)
CREATE_ROUND_STEP = 0.1


class ArchCanvas(QGraphicsView):
    """Canvas архитектурного редактора."""

    # x, y, w, d в МОДЕЛЬНЫХ координатах
    create_requested = Signal(float, float, float, float)

    def __init__(self, scene: ArchScene, parent=None):
        super().__init__(scene, parent)

        self._panning = False
        self._pan_start = QPoint()

        # Текущий инструмент
        self._tool = "select"

        # Preview-прямоугольник для drag-to-create
        self._create_start: QPointF | None = None
        self._preview: QGraphicsRectItem | None = None

        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.NoAnchor
        )
        self.setResizeAnchor(
            QGraphicsView.ViewportAnchor.NoAnchor
        )
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMouseTracking(True)

        # Фокус для клавиатуры
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.reset_view()

    # ============================================================
    # TOOL
    # ============================================================

    def current_tool(self) -> str:
        return self._tool

    def set_tool(self, tool: str) -> None:
        """Переключает инструмент. Отменяет текущий preview."""
        if tool not in ("select", "room"):
            return

        self._cancel_preview()

        self._tool = tool

        if tool == "room":
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    # ============================================================
    # ZOOM
    # ============================================================

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            super().wheelEvent(event)
            return

        delta = event.angleDelta().y()
        if delta == 0:
            return

        factor = 1.1 ** (delta / 120.0)
        anchor = event.position().toPoint()
        self._zoom_by(factor, anchor)
        event.accept()

    def _zoom_by(self, factor: float, viewport_anchor: QPoint) -> None:
        current_ppm = self.current_ppm()
        new_ppm = current_ppm * factor

        if new_ppm < PPM_MIN or new_ppm > PPM_MAX:
            return

        scene_pos_before = self.mapToScene(viewport_anchor)
        self.scale(factor, factor)
        scene_pos_after = self.mapToScene(viewport_anchor)
        delta = scene_pos_after - scene_pos_before
        self.translate(delta.x(), delta.y())

    def current_ppm(self) -> float:
        return abs(self.transform().m11())

    # ============================================================
    # MOUSE
    # ============================================================

    def mousePressEvent(self, event) -> None:
        # Middle mouse → pan всегда
        if event.button() == Qt.MouseButton.MiddleButton:
            self._start_pan(event)
            return

        # Инструмент room → начало drag-to-create
        if (
            self._tool == "room"
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self._start_create(event)
            return

        # Shift+drag → pan
        if (
            event.button() == Qt.MouseButton.LeftButton
            and event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self._start_pan(event)
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._panning:
            self._continue_pan(event)
            return

        if self._preview is not None:
            self._update_create(event)
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._panning and event.button() in (
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.MiddleButton,
        ):
            self._end_pan(event)
            return

        if self._preview is not None:
            self._finish_create(event)
            return

        super().mouseReleaseEvent(event)

    # ============================================================
    # PAN
    # ============================================================

    def _start_pan(self, event) -> None:
        self._panning = True
        self._pan_start = event.position().toPoint()
        self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
        event.accept()

    def _continue_pan(self, event) -> None:
        current = event.position().toPoint()
        delta = current - self._pan_start
        self._pan_start = current

        self.horizontalScrollBar().setValue(
            self.horizontalScrollBar().value() - delta.x()
        )
        self.verticalScrollBar().setValue(
            self.verticalScrollBar().value() - delta.y()
        )
        event.accept()

    def _end_pan(self, event) -> None:
        self._panning = False
        if self._tool == "room":
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        event.accept()

    # ============================================================
    # DRAG-TO-CREATE
    # ============================================================

    def _start_create(self, event) -> None:
        scene_pos = self.mapToScene(event.position().toPoint())
        self._create_start = scene_pos

        # Preview
        preview = QGraphicsRectItem()
        pen = QPen(QColor("#7AAAD0"), 1.5)
        pen.setCosmetic(True)
        pen.setStyle(Qt.PenStyle.DashLine)
        preview.setPen(pen)

        fill = QColor("#3A5A7A")
        fill.setAlpha(60)
        preview.setBrush(QBrush(fill))

        preview.setZValue(1000)   # поверх всего
        self.scene().addItem(preview)
        self._preview = preview

        event.accept()

    def _update_create(self, event) -> None:
        if self._create_start is None or self._preview is None:
            return

        current = self.mapToScene(event.position().toPoint())
        rect = self._normalized_rect(self._create_start, current)

        # Мини-размер для отображения preview
        min_scene = 0.01
        if rect[2] < min_scene or rect[3] < min_scene:
            self._preview.setRect(0, 0, 0, 0)
        else:
            self._preview.setRect(*rect)

        event.accept()

    def _finish_create(self, event) -> None:
        if self._create_start is None or self._preview is None:
            self._cancel_preview()
            return

        current = self.mapToScene(event.position().toPoint())
        sx, sy, sw, sd = self._normalized_rect(self._create_start, current)

        self._cancel_preview()

        # Игнор слишком мелких
        if sw < MIN_CREATE_SIZE or sd < MIN_CREATE_SIZE:
            self.set_tool("select")
            event.accept()
            return

        # Конвертация в модель
        # sx, sy — левый-верхний угол в scene (Y↓)
        # В модели нижний-левый: model_y = -(sy + sd)
        model_x = self._round(sx, CREATE_ROUND_STEP)
        model_y = self._round(-(sy + sd), CREATE_ROUND_STEP)
        model_w = self._round(sw, CREATE_ROUND_STEP)
        model_d = self._round(sd, CREATE_ROUND_STEP)

        # Мини-проверка после округления
        if model_w < MIN_CREATE_SIZE or model_d < MIN_CREATE_SIZE:
            self.set_tool("select")
            event.accept()
            return

        self.create_requested.emit(
            model_x, model_y, model_w, model_d
        )

        # Сброс в select
        self.set_tool("select")

        event.accept()

    def _cancel_preview(self) -> None:
        if self._preview is not None:
            scene = self.scene()
            if scene is not None:
                scene.removeItem(self._preview)
            self._preview = None

        self._create_start = None

    @staticmethod
    def _normalized_rect(p1: QPointF, p2: QPointF) -> tuple[float, float, float, float]:
        """Нормализует прямоугольник: (left, top, w, h)."""
        x = min(p1.x(), p2.x())
        y = min(p1.y(), p2.y())
        w = abs(p2.x() - p1.x())
        h = abs(p2.y() - p1.y())
        return (x, y, w, h)

    @staticmethod
    def _round(value: float, step: float) -> float:
        return round(value / step) * step

    # ============================================================
    # KEYBOARD
    # ============================================================

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_0:
            self.reset_view()
            event.accept()
            return

        if event.key() == Qt.Key.Key_Escape:
            if self._preview is not None:
                self._cancel_preview()
                event.accept()
                return
            if self._tool != "select":
                self.set_tool("select")
                event.accept()
                return

        super().keyPressEvent(event)

    # ============================================================
    # RESET
    # ============================================================

    def reset_view(self) -> None:
        self.resetTransform()
        self.scale(PPM_DEFAULT, PPM_DEFAULT)
        self.centerOn(0.0, 0.0)

    # ============================================================
    # КОНВЕРТАЦИИ
    # ============================================================

    def meters_to_pixels(self, meters: float) -> float:
        return meters * self.current_ppm()

    def pixels_to_meters(self, pixels: float) -> float:
        ppm = self.current_ppm()
        if ppm == 0:
            return 0.0
        return pixels / ppm
