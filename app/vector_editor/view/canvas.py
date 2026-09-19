"""
VectorCanvas — QGraphicsView с pan/zoom.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QGraphicsView

from .scene import VectorScene


PPM_MIN = 2.0
PPM_MAX = 2000.0
PPM_DEFAULT = 50.0


class VectorCanvas(QGraphicsView):
    """Canvas с pan/zoom. Координаты в метрах."""

    def __init__(self, scene: VectorScene, parent=None):
        super().__init__(scene, parent)

        self._panning = False
        self._pan_start = QPoint()

        self.setDragMode(QGraphicsView.DragMode.NoDrag)

        # Полная перерисовка viewport — избегаем артефактов
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.NoAnchor
        )
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Рендер
        self.setRenderHint(self.renderHints())

        self.reset_view()

    # ------------------------------------------------------------

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        if delta == 0:
            return

        factor = 1.1 ** (delta / 120.0)
        anchor = event.position().toPoint()
        self._zoom_by(factor, anchor)
        event.accept()

    def _zoom_by(self, factor: float, viewport_anchor: QPoint) -> None:
        current_ppm = abs(self.transform().m11())
        new_ppm = current_ppm * factor
        if new_ppm < PPM_MIN or new_ppm > PPM_MAX:
            return

        before = self.mapToScene(viewport_anchor)
        self.scale(factor, factor)
        after = self.mapToScene(viewport_anchor)
        delta = after - before
        self.translate(delta.x(), delta.y())

    def current_ppm(self) -> float:
        return abs(self.transform().m11())

    # ------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._start_pan(event)
            return
        if (
            event.button() == Qt.MouseButton.LeftButton
            and event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self._start_pan(event)
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
        if self._panning and event.button() in (
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.MiddleButton,
        ):
            self._panning = False
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _start_pan(self, event) -> None:
        self._panning = True
        self._pan_start = event.position().toPoint()
        self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
        event.accept()

    # ------------------------------------------------------------

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_0:
            self.reset_view()
            event.accept()
            return
        super().keyPressEvent(event)

    def reset_view(self) -> None:
        self.resetTransform()
        self.scale(PPM_DEFAULT, PPM_DEFAULT)
        self.centerOn(0.0, 0.0)
