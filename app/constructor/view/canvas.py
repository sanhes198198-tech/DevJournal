"""
ConstructorCanvas — QGraphicsView, Y ↑, pan, zoom.
"""
from __future__ import annotations
from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QGraphicsView
from .scene import ConstructorScene

PPM_MIN = 2.0
PPM_MAX = 2000.0
PPM_DEFAULT = 50.0


class ConstructorCanvas(QGraphicsView):
    mouse_moved = Signal(float, float)

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self._panning = False
        self._pan_start = QPoint()
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self._centered_once = False
        self.reset_view()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Центрируем в (0,0) один раз, после первого показа окна.
        # До показа viewport имеет нулевой размер, centerOn даёт смещение.
        if not self._centered_once:
            self._centered_once = True
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, self._center_on_origin)

    def _center_on_origin(self) -> None:
        self.centerOn(0.0, 0.0)

    def current_ppm(self) -> float:
        return abs(self.transform().m11())

    def reset_view(self) -> None:
        self.resetTransform()
        # Y↑ делается в ComponentItem через флип контура.
        # Здесь — Qt-нативный Y↓.
        self.scale(PPM_DEFAULT, PPM_DEFAULT)
        self.centerOn(0.0, 0.0)

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = 1.1 ** (delta / 120.0)
        self._zoom_by(factor, event.position().toPoint())
        event.accept()

    def _zoom_by(self, factor: float, anchor: QPoint) -> None:
        new_ppm = self.current_ppm() * factor
        if new_ppm < PPM_MIN or new_ppm > PPM_MAX:
            return
        before = self.mapToScene(anchor)
        self.scale(factor, factor)
        after = self.mapToScene(anchor)
        delta = after - before
        self.translate(delta.x(), delta.y())

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.position().toPoint()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()
            return
        if (event.button() == Qt.MouseButton.LeftButton
                and event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
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
                self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y())
            event.accept()
            return
        sp = self.mapToScene(event.position().toPoint())
        self.mouse_moved.emit(sp.x(), sp.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._panning and event.button() in (
                Qt.MouseButton.LeftButton, Qt.MouseButton.MiddleButton):
            self._panning = False
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_0:
            self.reset_view()
            event.accept()
            return
        super().keyPressEvent(event)
