"""
VectorEditor — QMainWindow для теста V0.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow,
    QToolBar,
    QLabel,
    QStatusBar,
)

from .model.contour import VectorContour
from .view.scene import VectorScene
from .view.canvas import VectorCanvas
from .view.items.contour_item import ContourItem


class VectorEditor(QMainWindow):
    """Окно векторного редактора (V0)."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Vector Architecture Editor — V0")
        self.resize(1200, 800)

        self._scene = VectorScene(self)
        self._canvas = VectorCanvas(self._scene, self)

        self._contour_item: ContourItem | None = None
        self._counter = 0

        self.setCentralWidget(self._canvas)
        self.setStatusBar(QStatusBar(self))
        self._build_toolbar()

        self.statusBar().showMessage(
            "Колесо — zoom · Shift+drag / middle — pan · 0 — reset"
        )

    # ------------------------------------------------------------

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main", self)
        tb.setMovable(False)
        self.addToolBar(tb)

        act_new = QAction("Новый контур", self)
        act_new.setShortcut(QKeySequence("Ctrl+N"))
        act_new.triggered.connect(self._on_new_contour)
        tb.addAction(act_new)

        tb.addSeparator()

        act_reset = QAction("Сбросить вид", self)
        act_reset.setShortcut(QKeySequence("Ctrl+0"))
        act_reset.triggered.connect(self._canvas.reset_view)
        tb.addAction(act_reset)

    # ------------------------------------------------------------

    def _on_new_contour(self) -> None:
        if self._contour_item is not None:
            self._scene.removeItem(self._contour_item)
            self._contour_item = None

        self._counter += 1
        contour = VectorContour.create_test_pentagon(
            cx=0.0, cy=0.0, r=3.0
        )
        contour.name = f"Контур {self._counter}"

        item = ContourItem(contour)
        self._scene.addItem(item)
        self._contour_item = item

        self.statusBar().showMessage(
            f"Создан «{contour.name}» ({contour.count()} узлов). "
            f"Тяни узлы мышью.", 4000
        )
