"""
ArchCanvas — QGraphicsView архитектурного редактора.

Управление:
  - Ctrl + wheel  → zoom к курсору
  - Space + drag  → pan
  - Middle drag   → pan
  - Клавиша 0     → сброс zoom/pan

Координаты: метры. Y↓ (Qt native).
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QGraphicsView

from .scene import ArchScene


# Ограничения zoom (pixels per meter)
PPM_MIN = 0.05   # 1 пиксель = 20 метров
PPM_MAX = 20.0   # 1 метр = 20 пикселей


# Начальный zoom
PPM_DEFAULT = 50.0


class ArchCanvas(QGraphicsView):
    """Canvas архитектурного редактора."""

    def __init__(self, scene: ArchScene, parent=None):
        super().__init__(scene, parent)

        self._panning = False
        self._pan_start = QPoint()

        self.setRenderHint(self.renderHints())
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

        self.reset_view()

    # ============================================================
    # ZOOM
    # ============================================================

    def wheelEvent(self, event) -> None:
        """Ctrl + wheel — zoom. Иначе — стандартный скролл."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta == 0:
                return

            factor = 1.1 ** (delta / 120.0)
            anchor = event.position().toPoint()
            self._zoom_by(factor, anchor)
            event.accept()
        else:
            super().wheelEvent(event)

    def _zoom_by(self, factor: float, viewport_anchor: QPoint) -> None:
        """Zoom с ограничением и anchor под курсором."""
        current_ppm = self.current_ppm()
        new_ppm = current_ppm * factor

        if new_ppm < PPM_MIN or new_ppm > PPM_MAX:
            return

        # Anchor: точка сцены под курсором
        scene_pos_before = self.mapToScene(viewport_anchor)

        self.scale(factor, factor)

        # Сдвинуть, чтобы точка сцены осталась под курсором
        scene_pos_after = self.mapToScene(viewport_anchor)
        delta = scene_pos_after - scene_pos_before
        self.translate(delta.x(), delta.y())

    def current_ppm(self) -> float:
        """Текущий zoom в пикселях на метр."""
        return abs(self.transform().m11())

    # ============================================================
    # PAN
    # ============================================================

    def mousePressEvent(self, event) -> None:
        if self._should_start_pan(event):
            self._panning = True
            self._pan_start = event.position().toPoint()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._panning:
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
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._panning:
            self._panning = False
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _should_start_pan(self, event) -> bool:
        """Pan: Space+drag ЛКМ или middle mouse."""
        if event.button() == Qt.MouseButton.MiddleButton:
            return True
        if (
            event.button() == Qt.MouseButton.LeftButton
            and event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            # Shift+drag тоже pan — удобно, если Space занят
            return True
        # Позже добавим Space через keyPressEvent
        return False

    # ============================================================
    # RESET
    # ============================================================

    def reset_view(self) -> None:
        """Сброс zoom и pan к дефолту."""
        self.resetTransform()
        self.scale(PPM_DEFAULT, PPM_DEFAULT)
        self.centerOn(0.0, 0.0)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_0:
            self.reset_view()
            event.accept()
            return
        super().keyPressEvent(event)

    # ============================================================
    # КОНВЕРТАЦИИ (для будущего M1)
    # ============================================================

    def meters_to_pixels(self, meters: float) -> float:
        return meters * self.current_ppm()

    def pixels_to_meters(self, pixels: float) -> float:
        ppm = self.current_ppm()
        if ppm == 0:
            return 0.0
        return pixels / ppm
