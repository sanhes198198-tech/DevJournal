"""
VectorCanvas — QGraphicsView с pan/zoom и двумя режимами:

  - "select"  → выделение, pan, drag узлов
  - "draw"    → создание нового контура кликами

В режиме draw:
  - ЛКМ → поставить точку
  - ЛКМ рядом с первой точкой (и точек ≥ 3) → замкнуть контур
  - Enter → замкнуть контур (если точек ≥ 3)
  - Esc → отмена
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPoint, QPointF, Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QGraphicsView

from .scene import VectorScene
from .items.drawing_preview import DrawingPreviewItem
from ..model.contour import VectorContour


PPM_MIN = 2.0
PPM_MAX = 2000.0
PPM_DEFAULT = 50.0

# Радиус (в пикселях экрана), внутри которого клик по первой точке
# в режиме draw считается замыканием.
CLOSE_PIXELS = 12.0


class VectorCanvas(QGraphicsView):
    """Canvas с pan/zoom и режимами select/draw."""

    # Готовый новый контур (замкнутый)
    contour_created = Signal(object)
    # Клик по сцене, не попавший ни в узел, ни в ребро
    empty_click = Signal()
    # Extrude-режим: клик в сцене — создать новую точку
    extrude_click = Signal(float, float)
    # Extrude-режим отменён (Esc) или завершён
    extrude_finished = Signal()

    def __init__(self, scene: VectorScene, parent=None):
        super().__init__(scene, parent)

        self._panning = False
        self._pan_start = QPoint()

        self._tool = "select"

        # Preview для режима draw
        self._preview: DrawingPreviewItem | None = None
        # Anchor для preview в extrude-режиме (scene coords в метрах)
        self._extrude_anchor: tuple[float, float] | None = None

        self.setDragMode(QGraphicsView.DragMode.NoDrag)
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

        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )

        self.reset_view()

    # ============================================================
    # TOOL
    # ============================================================

    def current_tool(self) -> str:
        return self._tool

    def set_tool(self, tool: str) -> None:
        if tool not in ("select", "draw", "extrude"):
            return

        if tool != "draw":
            self._cancel_preview()

        self._tool = tool

        if tool in ("draw", "extrude"):
            self.setFocus()
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            # Уходя из extrude — убрать preview
            if self._extrude_anchor is not None:
                self._extrude_anchor = None
                self.viewport().update()

        # Уходя из extrude — сообщить наружу
        if tool != "extrude":
            pass   # editor сам знает про смену режима

    # ============================================================
    # ZOOM
    # ============================================================

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

    # ============================================================
    # MOUSE
    # ============================================================

    def mousePressEvent(self, event) -> None:
        # Middle → pan всегда
        if event.button() == Qt.MouseButton.MiddleButton:
            self._start_pan(event)
            return

        # ЛКМ в select-режиме без Shift: если клик не попал ни в узел,
        # ни в ребро — сигналим наружу и НЕ пропускаем в scene.
        if (
            self._tool == "select"
            and event.button() == Qt.MouseButton.LeftButton
            and not (
                event.modifiers()
                & Qt.KeyboardModifier.ShiftModifier
            )
        ):
            scene_pos = self.mapToScene(event.position().toPoint())
            if not self._hit_test_node_or_edge(scene_pos):
                self.empty_click.emit()
                event.accept()
                return

        # Shift + ЛКМ → pan всегда
        if (
            event.button() == Qt.MouseButton.LeftButton
            and event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self._start_pan(event)
            return

        # draw → клик по сцене
        if (
            self._tool == "draw"
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self._on_draw_click(event)
            return

        # extrude → клик создаёт новую точку
        if (
            self._tool == "extrude"
            and event.button() == Qt.MouseButton.LeftButton
        ):
            scene_pos = self.mapToScene(
                event.position().toPoint()
            )
            self.extrude_click.emit(scene_pos.x(), scene_pos.y())
            event.accept()
            return

        # select → обычная логика QGraphicsView (drag узлов)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._panning:
            self._pan_move(event)
            return

        # draw → обновляем «резинку»
        if self._tool == "draw" and self._preview is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            self._preview.set_cursor(scene_pos.x(), scene_pos.y())
            event.accept()
            return

        # extrude → просто перерисовать (для preview-линии)
        if self._tool == "extrude" and self._extrude_anchor is not None:
            self.viewport().update()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._panning and event.button() in (
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.MiddleButton,
        ):
            self._panning = False
            if self._tool == "draw":
                self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
            else:
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            event.accept()
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

    def _pan_move(self, event) -> None:
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

    # ============================================================
    # DRAW MODE
    # ============================================================

    def _hit_test_node_or_edge(self, scene_pos) -> bool:
        """True, если клик попал в NodeItem или в ребро ContourItem."""
        from .items.node_item import NodeItem
        from .items.contour_item import ContourItem

        items = self.scene().items(scene_pos)

        for it in items:
            if isinstance(it, NodeItem):
                return True

        for it in items:
            if isinstance(it, ContourItem):
                try:
                    idx = it._find_edge_at(
                        scene_pos.x(), scene_pos.y(),
                    )
                except Exception:
                    idx = None
                if idx is not None:
                    return True

        return False

    def set_extrude_anchor(self, x: float, y: float) -> None:
        """Запомнить точку старта вытягивания для preview-линии."""
        self._extrude_anchor = (float(x), float(y))
        self.viewport().update()

    def clear_extrude_anchor(self) -> None:
        self._extrude_anchor = None
        self.viewport().update()

    def _on_draw_click(self, event) -> None:
        # Гарантируем фокус, чтобы клавиши (Esc / Backspace) шли сюда
        self.setFocus()
        scene_pos = self.mapToScene(event.position().toPoint())

        # Первый клик — создаём preview
        if self._preview is None:
            self._preview = DrawingPreviewItem()
            self.scene().addItem(self._preview)

        # Если уже есть >= 3 точки и клик близко к первой — замыкаем
        if self._preview.count() >= 3:
            first = self._preview.first_point()
            if first is not None:
                ppm = self.current_ppm() or 1.0
                dist_px = math.hypot(
                    scene_pos.x() - first[0],
                    scene_pos.y() - first[1],
                ) * ppm

                if dist_px < CLOSE_PIXELS:
                    self._finish_drawing()
                    event.accept()
                    return

        # Иначе — добавляем точку
        self._preview.add_point(scene_pos.x(), scene_pos.y())
        self._preview.set_cursor(scene_pos.x(), scene_pos.y())

        event.accept()

    def _finish_drawing(self, closed: bool = True) -> None:
        """Завершить черновик.

        closed=True  → замкнутый контур
        closed=False → разомкнутая полилиния (Shift+Enter)
        """
        if self._preview is None or self._preview.count() < 2:
            self._cancel_preview()
            return

        # Для замкнутого нужно ≥ 3 точек
        if closed and self._preview.count() < 3:
            self._cancel_preview()
            return

        points = list(self._preview._points)
        contour = VectorContour(
            points=points,
            closed=closed,
            name="Контур",
        )

        self._cancel_preview()
        self.contour_created.emit(contour)

    def _cancel_preview(self) -> None:
        if self._preview is not None:
            scene = self.scene()
            if scene is not None:
                scene.removeItem(self._preview)
            self._preview = None

    # ============================================================
    # KEYBOARD
    # ============================================================

    def keyPressEvent(self, event) -> None:
        # 0 → reset view
        if event.key() == Qt.Key.Key_0:
            self.reset_view()
            event.accept()
            return

        # Esc → отмена текущего контура в draw, выход в select
        if event.key() == Qt.Key.Key_Escape:
            if self._preview is not None:
                self._cancel_preview()
                event.accept()
                return
            if self._tool == "extrude":
                self.extrude_finished.emit()
                self.set_tool("select")
                event.accept()
                return
            if self._tool != "select":
                self.set_tool("select")
                event.accept()
                return

        # Enter → завершить extrude (если ничего не строим)
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._tool == "extrude":
                self.extrude_finished.emit()
                self.set_tool("select")
                event.accept()
                return

        # Enter → замкнуть контур (≥3 точки)
        # Shift+Enter → завершить разомкнутым (≥2 точки)
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._preview is not None:
                shift = bool(
                    event.modifiers()
                    & Qt.KeyboardModifier.ShiftModifier
                )
                if shift and self._preview.count() >= 2:
                    self._finish_drawing(closed=False)
                    event.accept()
                    return
                if (
                    not shift
                    and self._preview.count() >= 3
                ):
                    self._finish_drawing(closed=True)
                    event.accept()
                    return

        super().keyPressEvent(event)

    # ============================================================
    # RESET
    # ============================================================

    def drawForeground(self, painter, rect) -> None:
        """Preview-линия в extrude-режиме: от anchor к курсору."""
        super().drawForeground(painter, rect)

        if (
            self._tool != "extrude"
            or self._extrude_anchor is None
        ):
            return

        cursor_scene = self.mapToScene(
            self.viewport().mapFromGlobal(QCursor.pos())
        )

        from PySide6.QtGui import QPen, QColor
        from PySide6.QtCore import QPointF

        pen = QPen(QColor("#0078D4"), 0)
        pen.setCosmetic(True)
        pen.setStyle(__import__("PySide6.QtCore", fromlist=["Qt"])
                     .Qt.PenStyle.DashLine)
        painter.setPen(pen)

        ax, ay = self._extrude_anchor
        painter.drawLine(
            QPointF(ax, ay),
            QPointF(cursor_scene.x(), cursor_scene.y()),
        )

    def reset_view(self) -> None:
        self.resetTransform()
        self.scale(PPM_DEFAULT, PPM_DEFAULT)
        self.centerOn(0.0, 0.0)
