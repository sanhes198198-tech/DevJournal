"""
VectorEditor — QMainWindow V4.

Возможности:
  - Создание контура мышью (Ctrl+N → draw mode)
  - Move / add / remove узлов
  - Extrude грани (Ctrl+E)
  - Asset Browser слева (двойной клик → открыть)
  - Save (Ctrl+S) — обновить текущий
  - Save As (Ctrl+Shift+S) — создать новый
  - New (Ctrl+N) — пустая сцена
  - Undo (Ctrl+Z) для extrude / remove node
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QSplitter,
    QToolBar,
    QStatusBar,
)

from .model.contour import VectorContour
from .model.asset import Asset
from .io import (
    save_asset, load_asset,
    StorageError, delete_asset,
)
from .view.scene import VectorScene
from .view.canvas import VectorCanvas
from .view.asset_browser import AssetBrowser
from .view.save_asset_dialog import SaveAssetDialog
from .view.items.contour_item import ContourItem
from .view.items.node_item import NodeItem


EXTRUDE_TEST_DISTANCE = 2.0


class VectorEditor(QMainWindow):
    """Окно векторного редактора (V4)."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Vector Architecture Editor — V4")
        self.resize(1400, 800)

        self._scene = VectorScene(self)
        self._canvas = VectorCanvas(self._scene, self)

        self._counter = 0
        self._undo_stack: list[tuple[ContourItem, list]] = []

        # Текущий Asset
        self._current_asset_id: str | None = None
        self._current_asset_name: str = "Новый"
        self._current_asset_type: str = "other"

        # Один контур на сцене (1A)
        self._contour_item: ContourItem | None = None

        # Флаг изменений
        self._modified = False

        self._build_ui()
        self._build_toolbar()
        self._connect_signals()
        self._update_title()

        self.statusBar().showMessage(
            "Ctrl+N — новый · Ctrl+S — сохранить · "
            "Ctrl+Shift+S — сохранить как · Ctrl+E — extrude"
        )

    # ============================================================
    # UI
    # ============================================================

    def _build_ui(self) -> None:
        self._browser = AssetBrowser()
        self._browser.refresh()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._browser)
        splitter.addWidget(self._canvas)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        self.setCentralWidget(splitter)
        self.setStatusBar(QStatusBar(self))

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main", self)
        tb.setMovable(False)
        self.addToolBar(tb)

        act_new = QAction("Новый", self)
        act_new.setShortcut(QKeySequence.StandardKey.New)
        act_new.setShortcutContext(
            Qt.ShortcutContext.ApplicationShortcut
        )
        act_new.triggered.connect(self._on_new)
        tb.addAction(act_new)

        act_save = QAction("Сохранить", self)
        act_save.setShortcut(QKeySequence("Ctrl+S"))
        act_save.triggered.connect(self._on_save)
        tb.addAction(act_save)

        act_save_as = QAction("Сохранить как…", self)
        act_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_save_as.triggered.connect(self._on_save_as)
        tb.addAction(act_save_as)

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

        act_reset = QAction("Сбросить вид", self)
        act_reset.setShortcut(QKeySequence("Ctrl+0"))
        act_reset.triggered.connect(self._canvas.reset_view)
        tb.addAction(act_reset)

    def _connect_signals(self) -> None:
        self._canvas.contour_created.connect(self._on_contour_created)
        self._browser.asset_open_requested.connect(self._on_open_asset)

    # ============================================================
    # TITLE / MODIFIED
    # ============================================================

    def _update_title(self) -> None:
        star = " *" if self._modified else ""
        self.setWindowTitle(
            f"{self._current_asset_name}{star} — Vector Editor V4"
        )

    def _mark_modified(self) -> None:
        if not self._modified:
            self._modified = True
            self._update_title()

    def _mark_saved(self) -> None:
        if self._modified:
            self._modified = False
            self._update_title()

    # ============================================================
    # NEW
    # ============================================================

    def _on_new(self) -> None:
        if not self._confirm_discard():
            return

        self._clear_scene()

        self._current_asset_id = None
        self._current_asset_name = "Новый"
        self._current_asset_type = "other"

        self._mark_saved()
        self._browser.clear_selection()

        # Входим в режим рисования — пустая сцена, ждём кликов
        self._canvas.set_tool("draw")
        self.statusBar().showMessage(
            "Нарисуйте контур: ЛКМ — точка · клик по первой или "
            "Enter — замкнуть · Esc — отмена", 8000
        )

    def _clear_scene(self) -> None:
        """Удалить всё со сцены безопасно.

        NodeItem — дочерние для ContourItem, поэтому сначала
        отцепляем их от родителей, потом удаляем всё.
        """
        # 1. Отцепляем NodeItem'ы, чтобы Qt не удалил их дважды
        for it in list(self._scene.items()):
            if isinstance(it, NodeItem):
                if it.scene() is not None:
                    it.setParentItem(None)
                    self._scene.removeItem(it)

        # 2. Удаляем оставшиеся (ContourItem и прочее)
        for it in list(self._scene.items()):
            if it.scene() is not None:
                self._scene.removeItem(it)

        self._contour_item = None
        self._undo_stack.clear()

    # ============================================================
    # DRAW → CONTOUR
    # ============================================================

    def _on_contour_created(self, contour: VectorContour) -> None:
        self._counter += 1
        contour.name = f"Контур {self._counter}"

        # Удаляем предыдущий (1A)
        if self._contour_item is not None:
            if self._contour_item.scene() is not None:
                self._scene.removeItem(self._contour_item)
            self._contour_item = None

        item = ContourItem(contour)
        item.changed.connect(self._on_contour_changed)
        self._scene.addItem(item)
        self._contour_item = item

        self._canvas.set_tool("select")
        self._scene.clearSelection()
        item.setSelected(True)

        self._mark_modified()

        self.statusBar().showMessage(
            f"Создан контур ({contour.count()} узлов). "
            f"Не забудьте сохранить (Ctrl+S).", 4000
        )

    def _on_contour_changed(self) -> None:
        self._mark_modified()

    # ============================================================
    # OPEN
    # ============================================================

    def _on_open_asset(self, asset_id: str) -> None:
        if not self._confirm_discard():
            return

        try:
            asset = load_asset(self._browser_asset_path(asset_id))
        except StorageError as e:
            QMessageBox.warning(
                self, "Ошибка загрузки",
                f"Не удалось загрузить Asset:\n\n{e}"
            )
            return

        self._load_asset_into_editor(asset)

    def _browser_asset_path(self, asset_id: str):
        """Путь к файлу Asset'а по id в глобальной библиотеке."""
        from .io import ASSETS_DIR
        return ASSETS_DIR / f"{asset_id}.json"

    def _load_asset_into_editor(self, asset: Asset) -> None:
        self._clear_scene()

        contour = VectorContour(
            points=asset.points(),
            closed=asset.is_closed(),
            name=asset.name,
        )

        item = ContourItem(contour)
        item.changed.connect(self._on_contour_changed)
        self._scene.addItem(item)
        self._contour_item = item

        self._current_asset_id = asset.id
        self._current_asset_name = asset.name
        self._current_asset_type = asset.type

        self._mark_saved()

        self._canvas.set_tool("select")
        self._scene.clearSelection()
        item.setSelected(True)

        self.statusBar().showMessage(
            f"Открыт: {asset.name} ({asset.type})", 4000
        )

    # ============================================================
    # SAVE
    # ============================================================

    def _on_save(self) -> None:
        if self._contour_item is None:
            self.statusBar().showMessage(
                "Нечего сохранять — нет контура", 3000
            )
            return

        if self._current_asset_id is None:
            # Нет id → это Save As
            self._on_save_as()
            return

        asset = Asset.from_contour(
            self._contour_item.contour,
            name=self._current_asset_name,
            type_=self._current_asset_type,
            asset_id=self._current_asset_id,
        )

        try:
            save_asset(asset)
        except StorageError as e:
            QMessageBox.critical(
                self, "Ошибка сохранения",
                f"Не удалось сохранить:\n\n{e}"
            )
            return

        self._mark_saved()
        self._browser.refresh()
        self.statusBar().showMessage(
            f"Сохранено: {asset.name}", 2000
        )

    def _on_save_as(self) -> None:
        if self._contour_item is None:
            self.statusBar().showMessage(
                "Нечего сохранять — нет контура", 3000
            )
            return

        dlg = SaveAssetDialog(
            default_name=self._current_asset_name or "Новый ассет",
            parent=self,
        )
        if dlg.exec() != SaveAssetDialog.DialogCode.Accepted:
            return

        asset = Asset.from_contour(
            self._contour_item.contour,
            name=dlg.result_name,
            type_=dlg.result_type,
        )

        try:
            save_asset(asset)
        except StorageError as e:
            QMessageBox.critical(
                self, "Ошибка сохранения",
                f"Не удалось сохранить:\n\n{e}"
            )
            return

        self._current_asset_id = asset.id
        self._current_asset_name = asset.name
        self._current_asset_type = asset.type

        self._mark_saved()
        self._browser.refresh()
        self.statusBar().showMessage(
            f"Создан новый Asset: {asset.name}", 3000
        )

    # ============================================================
    # EXTRUDE
    # ============================================================

    def _on_extrude(self) -> None:
        item = self._contour_item
        if item is None or not item.has_selected_edge():
            self.statusBar().showMessage(
                "Сначала кликните по грани контура", 3000
            )
            return

        snapshot = list(item.contour.points)

        ok = item.extrude_selected_face(EXTRUDE_TEST_DISTANCE)
        if not ok:
            self.statusBar().showMessage(
                "Не удалось вытянуть грань", 3000
            )
            return

        self._undo_stack.append((item, snapshot))
        self._mark_modified()
        self.statusBar().showMessage(
            f"Extrude на {EXTRUDE_TEST_DISTANCE} м", 2000
        )

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
        self._mark_modified()
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
        item = self._contour_item
        if item is None:
            return False

        node: NodeItem | None = None
        for it in self._scene.selectedItems():
            if isinstance(it, NodeItem):
                node = it
                break

        if node is None:
            return False

        pts = item.contour.points
        if len(pts) <= 3:
            self.statusBar().showMessage(
                "Нельзя удалить: у контура должно быть ≥ 3 узлов", 3000
            )
            return True

        snapshot = list(pts)
        item.remove_node(node.idx)
        self._undo_stack.append((item, snapshot))
        self._mark_modified()
        self.statusBar().showMessage("Узел удалён", 2000)
        return True

    # ============================================================
    # CLOSE
    # ============================================================

    def _confirm_discard(self) -> bool:
        """True — можно продолжать (сохранили или discard).
        False — пользователь отменил.
        """
        if not self._modified:
            return True

        result = QMessageBox.question(
            self,
            "Несохранённые изменения",
            f"Сохранить изменения в «{self._current_asset_name}»?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )

        if result == QMessageBox.StandardButton.Save:
            if self._current_asset_id is None:
                self._on_save_as()
                return not self._modified
            self._on_save()
            return not self._modified

        if result == QMessageBox.StandardButton.Discard:
            return True

        return False

    def closeEvent(self, event) -> None:
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()
