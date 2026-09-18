"""
QGraphicsView для редактора диалогов.

Поведение:
- колесо → zoom относительно курсора
- middle mouse → pan
- ЛКМ по пустому → rubber band selection
- ЛКМ по узлу → drag узла
"""

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsView, QFrame

from .scene import DialogueScene


class DialogueView(QGraphicsView):
    """Виджет просмотра и редактирования диалогового графа."""

    MIN_ZOOM = 25
    MAX_ZOOM = 300
    ZOOM_STEP = 5          # % за одно деление колеса

    def __init__(self, parent=None):
        super().__init__(parent)

        # Своя сцена
        self.dialogue_scene = DialogueScene(self)
        self.setScene(self.dialogue_scene)

        # Внешний вид
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.TextAntialiasing
        )

        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )

        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.NoAnchor
        )
        self.setResizeAnchor(
            QGraphicsView.ViewportAnchor.AnchorViewCenter
        )

        # Скроллбары — не показываем, но используем
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        # Режим drag: rubber band по пустому
        self.setDragMode(
            QGraphicsView.DragMode.RubberBandDrag
        )

        # Zoom
        self.zoom_factor = 1.0

        # Pan (middle mouse)
        self._panning = False
        self._pan_start = QPoint()

    # =========================================================
    # ZOOM
    # =========================================================

    def wheelEvent(self, event):
        """Zoom относительно курсора."""
        delta = event.angleDelta().y()

        if delta == 0:
            event.accept()
            return

        # Шаг в процентах
        step = self.ZOOM_STEP if delta > 0 else -self.ZOOM_STEP

        self._zoom_by(step, event.position().toPoint())
        event.accept()

    def _zoom_by(self, step_percent, viewport_pos):
        """Изменяет зум на step_percent относительно позиции."""
        current = int(self.zoom_factor * 100)
        target = current + step_percent
        target = max(self.MIN_ZOOM, min(self.MAX_ZOOM, target))

        if target == current:
            return

        new_factor = target / 100.0

        # Точка сцены под курсором до zoom
        scene_pos_before = self.mapToScene(viewport_pos)

        # Применяем zoom
        self.scale(
            new_factor / self.zoom_factor,
            new_factor / self.zoom_factor,
        )

        self.zoom_factor = new_factor

        # Точка сцены под курсором после zoom
        scene_pos_after = self.mapToScene(viewport_pos)

        # Сдвигаем view, чтобы под курсором была та же точка
        delta = scene_pos_after - scene_pos_before
        self.translate(delta.x(), delta.y())

    def zoom_in(self):
        center = self.viewport().rect().center()
        self._zoom_by(self.ZOOM_STEP * 2, center)

    def zoom_out(self):
        center = self.viewport().rect().center()
        self._zoom_by(-self.ZOOM_STEP * 2, center)

    def reset_zoom(self):
        """Сброс зума в 100%."""
        self.resetTransform()
        self.zoom_factor = 1.0

    # =========================================================
    # PAN — MIDDLE MOUSE
    # =========================================================

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.position().toPoint() - self._pan_start
            self._pan_start = event.position().toPoint()

            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )

            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.unsetCursor()
            event.accept()
            return

        super().mouseReleaseEvent(event)

    # =========================================================
    # УДОБНЫЕ ОБЁРТКИ
    # =========================================================

    def rebuild_from_model(self, dialogue):
        """Пересобирает сцену из модели."""
        self.dialogue_scene.rebuild_from_model(dialogue)

    def get_dialogue(self):
        return self.dialogue_scene.dialogue

    def sync_positions_to_model(self):
        self.dialogue_scene.sync_positions_to_model()
