"""
VectorEditor — QMainWindow для V1.

Режимы:
  - select  → обычное состояние (узлы можно таскать)
  - draw    → создание нового контура кликами

Клавиши:
  - Ctrl+N   → новый контур (вход в draw)
  - Esc      → отмена рисования / выход в select
  - Enter    → замкнуть контур (если точек ≥ 3)
  - Del/Back → удалить выделенный узел
  - 0        → сброс вида
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow,
    QToolBar,
    QStatusBar,
)

from .model.contour import VectorContour
from .view.scene import VectorScene
from .view.canvas import VectorCanvas
from .view.items.contour_item import ContourItem
from .view.items.node_item import NodeItem


class VectorEditor(QMainWindow):
    """Окно векторного редактора (V1)."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Vector Architecture Editor — V1")
        self.resize(1200, 800)

        self._scene = VectorScene(self)
        self._canvas = VectorCanvas(self._scene, self)

        self._counter = 0

        self.setCentralWidget(self._canvas)
        self.setStatusBar(QStatusBar(self))

        self._build_toolbar()
        self._connect_signals()

        self.statusBar().showMessage(
            "Ctrl+N — новый контур · 0 — сброс вида"
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

        act_cancel = QAction("Отмена", self)
        act_cancel.setShortcut(QKeySequence("Esc"))
        act_cancel.triggered.connect(self._on_cancel)
        tb.addAction(act_cancel)

        tb.addSeparator()

        act_reset = QAction("Сбросить вид", self)
        act_reset.setShortcut(QKeySequence("Ctrl+0"))
        act_reset.triggered.connect(self._canvas.reset_view)
        tb.addAction(act_reset)

    def _connect_signals(self) -> None:
        self._canvas.contour_created.connect(self._on_contour_created)

    # ------------------------------------------------------------

    def _on_new_contour(self) -> None:
        self._canvas.set_tool("draw")
        self.statusBar().showMessage(
            "ЛКМ — поставить точку · клик по первой точке или Enter — "
            "замкнуть · Esc — отмена", 8000
        )

    def _on_cancel(self) -> None:
        self._canvas.set_tool("select")

    def _on_contour_created(self, contour: VectorContour) -> None:
        self._counter += 1
        contour.name = f"Контур {self._counter}"

        item = ContourItem(contour)
        self._scene.addItem(item)

        # Вернуть в select и выделить новый контур
        self._canvas.set_tool("select")
        self._scene.clearSelection()
        item.setSelected(True)

        self.statusBar().showMessage(
            f"Создан «{contour.name}» ({contour.count()} узлов)", 4000
        )

    # ------------------------------------------------------------

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self._delete_selected_node():
                event.accept()
                return

        super().keyPressEvent(event)

    def _delete_selected_node(self) -> bool:
        """Удалить выделенный узел (если есть)."""
        node: NodeItem | None = None
        for it in self._scene.selectedItems():
            if isinstance(it, NodeItem):
                node = it
                break

        if node is None:
            return False

        parent = node.parentItem()
        if not isinstance(parent, ContourItem):
            return False

        pts = parent.contour.points
        if len(pts) <= 3:
            self.statusBar().showMessage(
                "Нельзя удалить: у контура должно быть ≥ 3 узлов", 3000
            )
            return True

        parent.remove_node(node.idx)
        self.statusBar().showMessage("Узел удалён", 2000)
        return True
