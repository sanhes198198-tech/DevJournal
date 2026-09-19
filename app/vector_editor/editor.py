"""
VectorEditor — QMainWindow для V3.

Возможности:
  - V1: draw mode (Ctrl+N), add/remove/insert узлов
  - V2: Extrude грани по нормали (Ctrl+E), Ctrl+Z
  - V3: Сохранить контур как Asset (Ctrl+S)
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
from .model.asset import Asset
from .io import save_asset, StorageError
from .view.scene import VectorScene
from .view.canvas import VectorCanvas
from .view.items.contour_item import ContourItem
from .view.items.node_item import NodeItem
from .view.save_asset_dialog import SaveAssetDialog


EXTRUDE_TEST_DISTANCE = 2.0


class VectorEditor(QMainWindow):
    """Окно векторного редактора."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Vector Architecture Editor — V3")
        self.resize(1200, 800)

        self._scene = VectorScene(self)
        self._canvas = VectorCanvas(self._scene, self)

        self._counter = 0
        self._undo_stack: list[tuple[ContourItem, list[tuple[float, float]]]] = []

        self.setCentralWidget(self._canvas)
        self.setStatusBar(QStatusBar(self))

        self._build_toolbar()
        self._connect_signals()

        self.statusBar().showMessage(
            "Ctrl+N — новый · Ctrl+E — Extrude · Ctrl+S — сохранить как Asset"
        )

    # ============================================================
    # UI
    # ============================================================

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main", self)
        tb.setMovable(False)
        self.addToolBar(tb)

        act_new = QAction("Новый контур", self)
        act_new.setShortcut(QKeySequence("Ctrl+N"))
        act_new.triggered.connect(self._on_new_contour)
        tb.addAction(act_new)

        act_cancel = QAction("Отмена действия", self)
        act_cancel.setShortcut(QKeySequence("Esc"))
        act_cancel.triggered.connect(self._on_cancel)
        tb.addAction(act_cancel)

        tb.addSeparator()

        act_extrude = QAction("Extrude (Ctrl+E)", self)
        act_extrude.setShortcut(QKeySequence("Ctrl+E"))
        act_extrude.triggered.connect(self._on_extrude)
        tb.addAction(act_extrude)

        act_undo = QAction("Отменить (Ctrl+Z)", self)
        act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        act_undo.triggered.connect(self._on_undo)
        tb.addAction(act_undo)

        tb.addSeparator()

        act_save = QAction("Сохранить как Asset… (Ctrl+S)", self)
        act_save.setShortcut(QKeySequence("Ctrl+S"))
        act_save.triggered.connect(self._on_save_asset)
        tb.addAction(act_save)

        tb.addSeparator()

        act_reset = QAction("Сбросить вид", self)
        act_reset.setShortcut(QKeySequence("Ctrl+0"))
        act_reset.triggered.connect(self._canvas.reset_view)
        tb.addAction(act_reset)

    def _connect_signals(self) -> None:
        self._canvas.contour_created.connect(self._on_contour_created)

    # ============================================================
    # DRAW
    # ============================================================

    def _on_new_contour(self) -> None:
        self._canvas.set_tool("draw")
        self.statusBar().showMessage(
            "ЛКМ — точка · клик по первой или Enter — замкнуть · Esc — отмена",
            8000,
        )

    def _on_cancel(self) -> None:
        self._canvas.set_tool("select")

    def _on_contour_created(self, contour: VectorContour) -> None:
        self._counter += 1
        contour.name = f"Контур {self._counter}"

        item = ContourItem(contour)
        self._scene.addItem(item)

        self._canvas.set_tool("select")
        self._scene.clearSelection()
        item.setSelected(True)

        self.statusBar().showMessage(
            f"Создан «{contour.name}» ({contour.count()} узлов)", 4000
        )

    # ============================================================
    # EXTRUDE
    # ============================================================

    def _on_extrude(self) -> None:
        item = self._find_contour_with_selected_edge()
        if item is None:
            self.statusBar().showMessage(
                "Сначала кликните по грани контура", 3000
            )
            return

        snapshot = list(item.contour.points)

        ok = item.extrude_selected_face(EXTRUDE_TEST_DISTANCE)
        if not ok:
            self.statusBar().showMessage("Не удалось вытянуть грань", 3000)
            return

        self._undo_stack.append((item, snapshot))
        self.statusBar().showMessage(
            f"Extrude на {EXTRUDE_TEST_DISTANCE} м", 2000
        )

    def _find_contour_with_selected_edge(self) -> ContourItem | None:
        for it in self._scene.items():
            if isinstance(it, ContourItem) and it.has_selected_edge():
                return it
        return None

    # ============================================================
    # SAVE AS ASSET
    # ============================================================

    def _on_save_asset(self) -> None:
        item = self._find_selected_contour()
        if item is None:
            self.statusBar().showMessage(
                "Выделите контур, чтобы сохранить как Asset", 3000
            )
            return

        default_name = item.contour.name or f"Контур {self._counter}"

        dlg = SaveAssetDialog(default_name=default_name, parent=self)
        if dlg.exec() != SaveAssetDialog.DialogCode.Accepted:
            return

        asset = Asset.from_contour(
            item.contour,
            name=dlg.result_name,
            type_=dlg.result_type,
        )

        try:
            path_saved = save_asset(asset)
        except StorageError as e:
            self.statusBar().showMessage(
                f"Ошибка сохранения: {e}", 5000
            )
            return

        self.statusBar().showMessage(
            f"Asset сохранён: {asset.name} → {path_saved.name}", 5000
        )

    def _find_selected_contour(self) -> ContourItem | None:
        """Найти ContourItem.

        Приоритет:
          1. Выделенный ContourItem
          2. Родитель выделенного NodeItem
          3. Единственный в сцене
        """
        for it in self._scene.selectedItems():
            if isinstance(it, ContourItem):
                return it

        for it in self._scene.selectedItems():
            if isinstance(it, NodeItem):
                parent = it.parentItem()
                if isinstance(parent, ContourItem):
                    return parent

        contours = [
            it for it in self._scene.items()
            if isinstance(it, ContourItem)
        ]
        if len(contours) == 1:
            return contours[0]

        return None

    # ============================================================
    # UNDO
    # ============================================================

    def _on_undo(self) -> None:
        if not self._undo_stack:
            self.statusBar().showMessage("Нечего отменять", 2000)
            return

        item, snapshot = self._undo_stack.pop()
        item.contour.points = list(snapshot)
        item._selected_edge_idx = None
        item._rebuild_nodes()
        item._rebuild_path()

        self.statusBar().showMessage("Отменено", 2000)

    # ============================================================
    # KEYBOARD
    # ============================================================

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self._delete_selected_node():
                event.accept()
                return

        super().keyPressEvent(event)

    def _delete_selected_node(self) -> bool:
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

        snapshot = list(pts)
        parent.remove_node(node.idx)
        self._undo_stack.append((parent, snapshot))
        self.statusBar().showMessage("Узел удалён", 2000)
        return True
