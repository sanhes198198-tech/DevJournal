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

from PySide6.QtCore import Qt, QEvent, QElapsedTimer, QBuffer, QIODevice
from PySide6.QtGui import QAction, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QSplitter,
    QToolBar,
    QStatusBar,
    QFileDialog,
)

from .model.contour import VectorContour
from .model.asset import Asset
from .io import (
    save_asset, load_asset,
    StorageError, delete_asset,
    save_reference_image_png,
    delete_reference_image_file,
    get_reference_image_path,
)
from .view.scene import VectorScene
from .view.canvas import VectorCanvas
from .view.asset_browser import AssetBrowser
from .view.semantic_groups_panel import SemanticGroupsPanel
from .view.parameters_panel import ParametersPanel
from .model.parameter import (
    compute_delta_for_parameter,
    apply_delta_to_points,
)
from .view.save_asset_dialog import SaveAssetDialog
from .view.items.contour_item import ContourItem
from .view.items.node_item import NodeItem
from .view.items.reference_item import ReferenceImageItem
from .view.reference_properties_dialog import ReferencePropertiesDialog
from .model.reference_image import ReferenceImage


EXTRUDE_TEST_DISTANCE = 2.0


class VectorEditor(QMainWindow):
    """Окно векторного редактора (V4)."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Vector Architecture Editor — V4")
        self.resize(1700, 800)

        self._scene = VectorScene(self)
        self._canvas = VectorCanvas(self._scene, self)

        self._counter = 0
        self._undo_stack: list[tuple] = []

        # Сессия слияния undo-записей от изменения параметра
        self._param_undo_active_id: str | None = None
        self._param_undo_timer = QElapsedTimer()

        # Снапшот перед началом ручного drag узла
        self._pending_drag_snapshot: list | None = None

        # Подложка под контур
        self._reference_item: ReferenceImageItem | None = None

        # Extrude-сессия (вытягивание из узла)
        self._extrude_source_idx: int | None = None
        self._extrude_points_added: int = 0

        # Текущий Asset (объект, не только id — нужен для групп)
        self._current_asset: Asset | None = None
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

        self._groups_panel = SemanticGroupsPanel()
        self._parameters_panel = ParametersPanel()

        # Правая колонка: сверху группы, снизу параметры
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.addWidget(self._groups_panel)
        right_splitter.addWidget(self._parameters_panel)
        right_splitter.setStretchFactor(0, 1)
        right_splitter.setStretchFactor(1, 1)
        right_splitter.setCollapsible(0, False)
        right_splitter.setCollapsible(1, False)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._browser)
        splitter.addWidget(self._canvas)
        splitter.addWidget(right_splitter)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setCollapsible(2, False)

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

        tb.addSeparator()

        act_ref_load = QAction("📷 Подложка", self)
        act_ref_load.setToolTip(
            "Загрузить картинку-подложку (PNG / JPG / BMP)"
        )
        act_ref_load.triggered.connect(self._on_load_reference)
        tb.addAction(act_ref_load)

        act_ref_props = QAction("⚙", self)
        act_ref_props.setToolTip("Свойства подложки")
        act_ref_props.triggered.connect(self._on_reference_properties)
        tb.addAction(act_ref_props)

        tb.addSeparator()

        act_clear = QAction("🧹 Очистить", self)
        act_clear.setShortcut(QKeySequence("Ctrl+Shift+N"))
        act_clear.setToolTip(
            "Удалить контур со сцены, подложку оставить "
            "(Ctrl+Shift+N)"
        )
        act_clear.triggered.connect(self._on_clear_contour)
        tb.addAction(act_clear)

        tb.addSeparator()

        # Разомкнуть / Замкнуть текущий контур
        act_toggle_closed = QAction("🔗", self)
        act_toggle_closed.setToolTip(
            "Разомкнуть / замкнуть текущий контур"
        )
        act_toggle_closed.triggered.connect(self._on_toggle_closed)
        tb.addAction(act_toggle_closed)

        # Скрыть / показать подложку
        act_toggle_ref = QAction("👁 Подложка", self)
        act_toggle_ref.setToolTip(
            "Скрыть / показать подложку"
        )
        act_toggle_ref.triggered.connect(self._on_toggle_reference)
        tb.addAction(act_toggle_ref)

        # Скрыть / показать узлы
        act_toggle_nodes = QAction("👁 Узлы", self)
        act_toggle_nodes.setToolTip(
            "Скрыть / показать квадратики узлов — "
            "чтобы посмотреть результат поверх подложки"
        )
        act_toggle_nodes.triggered.connect(self._on_toggle_nodes)
        tb.addAction(act_toggle_nodes)

        tb.addSeparator()

        act_ext_node = QAction("📐 Вытянуть", self)
        act_ext_node.setShortcut(
            QKeySequence("Ctrl+Shift+E")
        )
        act_ext_node.setToolTip(
            "Вытянуть линию из выделенного узла "
            "(Ctrl+Shift+E). Клик — новая точка. "
            "Esc / Enter — завершить."
        )
        act_ext_node.triggered.connect(self._on_extrude_node)
        tb.addAction(act_ext_node)

        act_extra = QAction("🔗 Соединить", self)
        act_extra.setShortcut(QKeySequence("Ctrl+J"))
        act_extra.setShortcutContext(
            Qt.ShortcutContext.ApplicationShortcut
        )
        act_extra.setToolTip(
            "Соединить два выделенных узла дополнительным ребром "
            "(Ctrl+J). Выделите два узла Ctrl+кликом."
        )
        act_extra.triggered.connect(self._on_add_extra_edge)
        tb.addAction(act_extra)

    def _connect_signals(self) -> None:
        self._canvas.contour_created.connect(self._on_contour_created)
        self._canvas.empty_click.connect(self._on_empty_scene_click)
        self._canvas.extrude_click.connect(self._on_extrude_click)
        self._canvas.extrude_finished.connect(
            self._on_extrude_finished
        )
        self._browser.asset_open_requested.connect(self._on_open_asset)
        self._browser.asset_delete_requested.connect(
            self._on_delete_asset
        )

        # Клик по пустому месту сцены — снимаем подсветку группы
        self._scene.installEventFilter(self)

        self._scene.selectionChanged.connect(
            self._on_scene_selection_changed
        )
        self._groups_panel.group_selected.connect(
            self._on_group_selected
        )
        self._groups_panel.groups_changed.connect(
            self._on_groups_changed
        )
        self._parameters_panel.value_changed.connect(
            self._on_parameter_value_changed
        )
        self._parameters_panel.parameters_changed.connect(
            self._on_groups_changed   # тот же обработчик: mark_modified
        )
        self._parameters_panel.parameter_selected.connect(
            self._on_parameter_selected
        )

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

    # ============================================================
    # SEMANTIC GROUPS
    # ============================================================

    def _on_scene_selection_changed(self) -> None:
        """Обновить список выделенных node_ids в панели групп."""
        node_ids = []
        for it in self._scene.selectedItems():
            if isinstance(it, NodeItem):
                nid = it.node_id
                if nid:
                    node_ids.append(nid)
        self._groups_panel.set_selected_node_ids(node_ids)

    def _on_group_selected(self, group_id: str) -> None:
        """Подсветить узлы выбранной группы.

        Пустой group_id → снять подсветку (например, после удаления).
        """
        if self._contour_item is None:
            return

        if not group_id:
            self._contour_item.clear_highlight()
            return

        if self._current_asset is None:
            self._contour_item.clear_highlight()
            return

        group = self._current_asset.get_semantic_group(group_id)
        if group is None:
            self._contour_item.clear_highlight()
            return

        self._contour_item.highlight_nodes(group.node_ids)

    PARAM_UNDO_MERGE_MS = 1500

    def _on_parameter_selected(self, param_id: str) -> None:
        """Клик по параметру — подсветить узлы всех его таргетов.

        Пустой param_id → снять подсветку.
        """
        if self._contour_item is None:
            return

        if not param_id or self._current_asset is None:
            self._contour_item.clear_highlight()
            return

        param = self._current_asset.get_parameter(param_id)
        if param is None:
            self._contour_item.clear_highlight()
            return

        # Собираем объединение node_ids всех таргетов
        node_ids: set[str] = set()
        for t in param.targets:
            group = self._current_asset.get_semantic_group(t.group_id)
            if group is None:
                continue
            node_ids.update(group.node_ids)

        if node_ids:
            self._contour_item.highlight_nodes(node_ids)
        else:
            self._contour_item.clear_highlight()

    def _on_parameter_value_changed(
        self, param_id: str, new_value: float, old_value: float,
    ) -> None:
        """Изменилось значение параметра — применить сдвиг к геометрии.

        Последовательные изменения ОДНОГО параметра с интервалом
        < PARAM_UNDO_MERGE_MS сливаются в одну undo-запись.
        """
        if self._current_asset is None or self._contour_item is None:
            return

        param = self._current_asset.get_parameter(param_id)
        if param is None:
            return

        delta_value = new_value - old_value
        if abs(delta_value) < 1e-12:
            return

        # --- Слияние серии изменений ---
        same_param = self._param_undo_active_id == param_id
        recent = (
            self._param_undo_timer.isValid()
            and self._param_undo_timer.elapsed()
                < self.PARAM_UNDO_MERGE_MS
        )

        if same_param and recent:
            # Продолжаем серию — snapshot НЕ пишем.
            pass
        else:
            # Новая серия: снапшот ДО текущего изменения.
            snapshot = list(self._contour_item.contour.points)
            self._undo_stack.append(
                (self._contour_item, snapshot, param_id, old_value)
            )
            self._param_undo_active_id = param_id
            self._param_undo_timer.restart()

        # --- Применяем сдвиг ---
        node_delta = compute_delta_for_parameter(
            param, delta_value, self._current_asset.semantic_groups,
        )

        if node_delta:
            new_points = apply_delta_to_points(
                self._contour_item.contour.points,
                self._contour_item.contour.node_ids,
                node_delta,
            )
            self._contour_item.contour.points = new_points
            self._contour_item._rebuild_nodes()
            self._contour_item._rebuild_path()

        param.value = new_value
        self._mark_modified()

    def _on_groups_changed(self) -> None:
        """Пользователь изменил группы — отметить Asset как изменённый."""
        self._mark_modified()

    @staticmethod
    def _prune_groups(groups: dict, valid_node_ids: list) -> dict:
        """Удалить группы, ссылающиеся на несуществующие узлы."""
        valid = set(valid_node_ids)
        result = {}
        for gid, g in groups.items():
            if all(nid in valid for nid in g.node_ids):
                result[gid] = g
        return result

    # ============================================================
    # REFERENCE IMAGE
    # ============================================================

    def _on_load_reference(self) -> None:
        """Загрузить картинку-подложку (контур не требуется)."""
        # Нужен сохранённый Asset (для имени файла подложки)
        if self._current_asset_id is None:
            reply = QMessageBox.question(
                self, "Asset не сохранён",
                "Для загрузки подложки Asset нужно сохранить.\n\n"
                "Сохранить сейчас (откроется диалог «Сохранить как»)?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            self._on_save_as()

            # Если пользователь отменил Save As — выходим
            if self._current_asset_id is None:
                return

        # После Save As точно есть _current_asset
        if self._current_asset is None:
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Загрузить подложку",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif)",
        )
        if not path:
            return

        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.warning(
                self, "Ошибка",
                "Не удалось открыть картинку.",
            )
            return

        # Конвертация в PNG-байты
        image = pixmap.toImage()
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        ok = image.save(buffer, "PNG")
        png_bytes = bytes(buffer.data())
        buffer.close()

        if not ok or not png_bytes:
            QMessageBox.warning(
                self, "Ошибка",
                "Не удалось конвертировать картинку в PNG.",
            )
            return

        # Сохранить файл
        try:
            filename = save_reference_image_png(
                self._current_asset_id, png_bytes,
            )
        except StorageError as e:
            QMessageBox.critical(
                self, "Ошибка сохранения",
                f"Не удалось записать подложку:\n\n{e}",
            )
            return

        # Удалить предыдущий PNG-файл (если был и не совпадает)
        old_ref = self._current_asset.reference_image
        if old_ref is not None and old_ref.filename != filename:
            delete_reference_image_file(old_ref.filename)

        # Обновить модель
        ref = ReferenceImage(filename=filename)
        self._current_asset.set_reference_image(ref)

        self._rebuild_reference_item()

        # Если контура нет — сразу переходим в draw-режим,
        # чтобы пользователь сразу начал обводить.
        if self._contour_item is None:
            self._canvas.set_tool("draw")
            if self._reference_item is not None:
                self._reference_item.set_interactive(False)
            self.statusBar().showMessage(
                f"Подложка загружена: {filename}. "
                f"Обводите: ЛКМ — точка · Enter — замкнуть · "
                f"Esc — отмена", 8000,
            )
        else:
            self.statusBar().showMessage(
                f"Подложка загружена: {filename}", 3000,
            )

        self._mark_modified()

    def _on_reference_properties(self) -> None:
        """Открыть диалог свойств подложки."""
        if (
            self._current_asset is None
            or not self._current_asset.has_reference_image()
        ):
            QMessageBox.information(
                self, "Нет подложки",
                "Сначала загрузите подложку (📷 Подложка).",
            )
            return

        ref = self._current_asset.reference_image
        dlg = ReferencePropertiesDialog(ref, self)
        if dlg.exec() != ReferencePropertiesDialog.DialogCode.Accepted:
            return

        if dlg.result_delete:
            delete_reference_image_file(ref.filename)
            self._current_asset.clear_reference_image()
            self._rebuild_reference_item()
            self._mark_modified()
            self.statusBar().showMessage("Подложка удалена", 2000)
            return

        dlg.apply_to_model()
        self._rebuild_reference_item()
        self._mark_modified()

    def _rebuild_reference_item(self) -> None:
        """Пересоздать ReferenceImageItem по модели Asset'а."""
        # Удалить текущий item
        if self._reference_item is not None:
            if self._reference_item.scene() is not None:
                self._scene.removeItem(self._reference_item)
            self._reference_item = None

        if (
            self._current_asset is None
            or not self._current_asset.has_reference_image()
        ):
            return

        ref = self._current_asset.reference_image
        path = get_reference_image_path(ref.filename)
        if not path.exists():
            return

        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return

        item = ReferenceImageItem(
            pixmap, pixels_per_meter=ref.pixels_per_meter,
        )
        # setPos до подключения сигнала — чтобы не считать это движение
        item.setPos(ref.x, ref.y)
        item.setOpacity(ref.opacity)
        item.setVisible(ref.visible)
        item.position_changed.connect(self._on_reference_moved)

        self._scene.addItem(item)
        self._reference_item = item

    def _on_reference_moved(self, x: float, y: float) -> None:
        """Подложку перетащили мышью."""
        if self._current_asset is None:
            return
        ref = self._current_asset.reference_image
        if ref is None:
            return
        ref.x = x
        ref.y = y
        self._mark_modified()

    # ============================================================
    # CLEAR CONTOUR (без подложки)
    # ============================================================

    def _remove_contour_only(self) -> None:
        """Удалить контур со сцены, подложку и Asset не трогать."""
        if self._contour_item is None:
            return
        if self._contour_item.scene() is not None:
            self._scene.removeItem(self._contour_item)
        self._contour_item = None
        self._undo_stack.clear()

    def _on_clear_contour(self) -> None:
        """Удалить контур со сцены, подложку оставить и войти в draw."""
        if self._contour_item is None:
            # Пусто — просто войти в draw
            self._canvas.set_tool("draw")
            if self._reference_item is not None:
                self._reference_item.set_interactive(False)
            self.statusBar().showMessage(
                "Нарисуйте контур: ЛКМ — точка · Backspace — "
                "убрать · Enter — замкнуть · Esc — отмена", 6000,
            )
            return

        if not self._confirm_discard():
            return

        self._remove_contour_only()
        self._mark_modified()

        self._canvas.set_tool("draw")
        if self._reference_item is not None:
            self._reference_item.set_interactive(False)

        self.statusBar().showMessage(
            "Контур очищен. Нарисуйте новый: ЛКМ — точка · "
            "Backspace — убрать · Enter — замкнуть · Esc — отмена",
            6000,
        )

    # ============================================================
    # VIEW TOGGLES (разомкнуть / скрыть подложку / скрыть узлы)
    # ============================================================

    def _on_toggle_closed(self) -> None:
        """Разомкнуть / замкнуть текущий контур."""
        if self._contour_item is None:
            self.statusBar().showMessage(
                "Нет контура — нечего замыкать / размыкать", 2000,
            )
            return

        contour = self._contour_item.contour
        contour.closed = not contour.closed

        # Перестроить путь (ребро исчезнет / появится)
        self._contour_item._rebuild_path()
        self._contour_item.changed.emit()

        state = "замкнут" if contour.closed else "разомкнут"
        self.statusBar().showMessage(
            f"Контур {state}", 2000,
        )

    def _on_toggle_reference(self) -> None:
        """Скрыть / показать подложку."""
        if (
            self._reference_item is None
            or self._current_asset is None
            or self._current_asset.reference_image is None
        ):
            self.statusBar().showMessage(
                "Подложки нет — загрузите (📷 Подложка)", 3000,
            )
            return

        ref = self._current_asset.reference_image
        ref.visible = not ref.visible
        self._reference_item.setVisible(ref.visible)

        state = "показана" if ref.visible else "скрыта"
        self.statusBar().showMessage(
            f"Подложка {state}", 2000,
        )

    def _on_toggle_nodes(self) -> None:
        """Скрыть / показать квадратики узлов."""
        if self._contour_item is None:
            self.statusBar().showMessage(
                "Нет контура", 2000,
            )
            return

        new_state = not self._contour_item.are_nodes_visible()
        self._contour_item.set_nodes_visible(new_state)

        state = "показаны" if new_state else "скрыты"
        self.statusBar().showMessage(
            f"Узлы {state}", 2000,
        )

    # ============================================================
    # EXTRUDE FROM NODE
    # ============================================================

    def _on_extrude_node(self) -> None:
        """Начать вытягивание линии из выделенного узла."""
        if self._contour_item is None:
            self.statusBar().showMessage(
                "Сначала откройте контур", 3000,
            )
            return

        # Выделен ровно один узел?
        selected_nodes = [
            it for it in self._scene.selectedItems()
            if isinstance(it, NodeItem)
        ]
        if len(selected_nodes) != 1:
            self.statusBar().showMessage(
                "Выделите ровно один узел (клик по квадратику), "
                "затем 📐 Вытянуть", 5000,
            )
            return

        idx = selected_nodes[0].idx
        self._extrude_source_idx = idx
        self._extrude_points_added = 0

        # Перейти в extrude-режим на canvas
        self._canvas.set_tool("extrude")

        # Anchor для preview — текущая позиция узла
        if 0 <= idx < len(self._contour_item.contour.points):
            ax, ay = self._contour_item.contour.points[idx]
            self._canvas.set_extrude_anchor(ax, ay)

        self.statusBar().showMessage(
            "Вытягивание: клик — новая точка. "
            "Enter / Esc — завершить.", 8000,
        )

    # Минимальное расстояние между создаваемыми точками (в пикселях)
    EXTRUDE_MIN_DIST_PX = 10.0

    def _on_extrude_click(self, x: float, y: float) -> None:
        """Клик в сцене в extrude-режиме — создать новую точку.

        Игнорирует клики ближе EXTRUDE_MIN_DIST_PX к предыдущей
        точке — защита от «наложения» при дрожании мыши или
        случайном двойном клике.
        """
        import math

        if (
            self._extrude_source_idx is None
            or self._contour_item is None
        ):
            return

        item = self._contour_item
        idx = self._extrude_source_idx

        # --- Попал в существующий узел? ---
        # Клик рядом с любым узлом контура (кроме последнего
        # созданного) → завершить extrude, новую точку не создавать.
        ppm = self._canvas.current_ppm() or 50.0
        HIT_RADIUS_PX = 12.0
        HIT_RADIUS_M = HIT_RADIUS_PX / ppm

        import math
        for i, (nx, ny) in enumerate(item.contour.points):
            # Пропускаем сам source (можно продолжать от него)
            if i == idx:
                continue
            if math.hypot(x - nx, y - ny) < HIT_RADIUS_M:
                self.statusBar().showMessage(
                    f"Клик в существующий узел "
                    f"({item.contour.node_ids[i]}). "
                    f"Extrude завершён. "
                    f"Для замыкания ветки нужно несколько "
                    f"контуров — это V8.",
                    8000,
                )
                self._on_extrude_finished()
                return

        # --- Проверка расстояния до предыдущей точки ---
        if 0 <= idx < len(item.contour.points):
            last_x, last_y = item.contour.points[idx]
            ppm = self._canvas.current_ppm() or 50.0
            dist_px = math.hypot(x - last_x, y - last_y) * ppm

            if dist_px < self.EXTRUDE_MIN_DIST_PX:
                self.statusBar().showMessage(
                    f"Слишком близко ({dist_px:.0f} px). "
                    f"Кликните дальше или Esc для завершения.",
                    2500,
                )
                return

        # Снапшот для undo
        snapshot = list(item.contour.points)

        new_node_id = item.contour.insert_point_after(idx, x, y)
        if new_node_id is None:
            self.statusBar().showMessage(
                "Не удалось добавить точку", 3000,
            )
            return

        item._rebuild_nodes()
        item._rebuild_path()

        self._undo_stack.append((item, snapshot))

        self._extrude_source_idx = idx + 1
        self._extrude_points_added += 1

        # Обновить anchor preview на новую точку
        self._canvas.set_extrude_anchor(x, y)

        self._mark_modified()

        self._scene.clearSelection()
        for node in item._nodes:
            if node.node_id == new_node_id:
                node.setSelected(True)
                break

        self.statusBar().showMessage(
            f"Точек: {self._extrude_points_added}. "
            f"Ещё клик — продолжить. Esc / Enter — завершить.",
            3000,
        )

    def _on_extrude_finished(self) -> None:
        """Extrude-сессия завершена (Esc / Enter)."""
        n = self._extrude_points_added
        self._extrude_source_idx = None
        self._extrude_points_added = 0
        self._canvas.set_tool("select")
        self._scene.clearSelection()

        if n > 0:
            self.statusBar().showMessage(
                f"Вытягивание завершено. Создано точек: {n}. "
                f"Ctrl+Z — отменить по одной.", 5000,
            )
        else:
            self.statusBar().showMessage(
                "Вытягивание завершено (точки не создавались)",
                2000,
            )

    def _reset_param_undo_session(self) -> None:
        """Закрыть текущую серию изменений одного параметра.

        Следующее изменение того же параметра начнёт новую undo-запись.
        """
        self._param_undo_active_id = None
        if self._param_undo_timer.isValid():
            self._param_undo_timer.invalidate()

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

        # Подложка не должна ловить клики в draw-режиме
        if self._reference_item is not None:
            self._reference_item.set_interactive(False)
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

        # Подложка
        if self._reference_item is not None:
            if self._reference_item.scene() is not None:
                self._scene.removeItem(self._reference_item)
            self._reference_item = None

        self._current_asset = None
        self._groups_panel.set_asset(None)
        self._parameters_panel.set_asset(None)

        self._reset_param_undo_session()

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
        item.node_drag_started.connect(self._on_node_drag_started)
        item.node_drag_finished.connect(self._on_node_drag_finished)
        self._scene.addItem(item)
        self._contour_item = item

        self._canvas.set_tool("select")
        self._scene.clearSelection()

        # Вернуть подложке способность двигаться
        if self._reference_item is not None:
            self._reference_item.set_interactive(True)

        self._mark_modified()

        self.statusBar().showMessage(
            f"Создан контур ({contour.count()} узлов). "
            f"Не забудьте сохранить (Ctrl+S).", 4000
        )

    def _on_contour_changed(self) -> None:
        # Ручное изменение геометрии (drag узла, extrude, insert и т.п.)
        # завершает текущую сессию изменения параметра.
        self._reset_param_undo_session()
        self._mark_modified()

    def _on_node_drag_started(self) -> None:
        """Пользователь начал тянуть узел — запомним снапшот."""
        if self._contour_item is None:
            return
        self._pending_drag_snapshot = list(
            self._contour_item.contour.points
        )

    def _on_node_drag_finished(self) -> None:
        """Пользователь отпустил узел — если что-то изменилось,
        кладём ОДНУ undo-запись.
        """
        snapshot = self._pending_drag_snapshot
        self._pending_drag_snapshot = None

        if snapshot is None or self._contour_item is None:
            return

        current = list(self._contour_item.contour.points)
        if current == snapshot:
            return

        # 2-tuple (item, snapshot) — совместимо с _on_undo
        self._undo_stack.append((self._contour_item, snapshot))

    # ============================================================
    # OPEN
    # ============================================================

    def _on_delete_asset(self, asset_id: str) -> None:
        """Удалить Asset из библиотеки."""
        is_current = (asset_id == self._current_asset_id)

        if is_current:
            msg = (
                f"Это текущий открытый Asset.\n\n"
                f"Закрыть его и удалить файл?"
            )
        else:
            msg = f"Удалить Asset {asset_id}?"

        reply = QMessageBox.question(
            self, "Удалить Asset", msg,
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Если удаляем текущий — сначала очищаем сцену
        if is_current:
            if not self._confirm_discard():
                return
            self._clear_scene()
            self._current_asset_id = None
            self._current_asset_name = "Новый"
            self._current_asset_type = "other"
            self._mark_saved()
            self._update_title()

        try:
            delete_asset(asset_id)
        except StorageError as e:
            QMessageBox.critical(
                self, "Ошибка удаления",
                f"Не удалось удалить:\n\n{e}",
            )
            return

        # Удалить картинку-подложку (если была)
        try:
            from .io import delete_reference_image_file
            delete_reference_image_file(f"{asset_id}_ref.png")
        except Exception:
            pass

        self._browser.refresh()
        self.statusBar().showMessage(
            f"Asset удалён: {asset_id}", 2000,
        )

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

        geometry = asset.geometry

        contour = VectorContour(
            points=asset.points(),
            node_ids=list(geometry.get("node_ids", [])),
            closed=asset.is_closed(),
            name=asset.name,
            extra_edges=asset.extra_edges(),
        )

        item = ContourItem(contour)
        item.changed.connect(self._on_contour_changed)
        item.node_drag_started.connect(self._on_node_drag_started)
        item.node_drag_finished.connect(self._on_node_drag_finished)
        self._scene.addItem(item)
        self._contour_item = item

        self._current_asset = asset
        self._current_asset_id = asset.id
        self._current_asset_name = asset.name
        self._current_asset_type = asset.type

        self._groups_panel.set_asset(asset)
        self._parameters_panel.set_asset(asset)

        # Подложка (если есть в Asset'е)
        self._rebuild_reference_item()
        if self._reference_item is not None:
            self._reference_item.set_interactive(True)

        self._mark_saved()

        self._canvas.set_tool("select")
        self._scene.clearSelection()

        self.statusBar().showMessage(
            f"Открыт: {asset.name} ({asset.type})", 4000
        )

    # ============================================================
    # SAVE
    # ============================================================

    def _on_save(self) -> None:
        if self._current_asset_id is None:
            # Нет id → это Save As (в т.ч. без контура)
            self._on_save_as()
            return

        if self._contour_item is not None:
            contour = self._contour_item.contour
        else:
            contour = VectorContour(points=[])

        asset = Asset.from_contour(
            contour,
            name=self._current_asset_name,
            type_=self._current_asset_type,
            asset_id=self._current_asset_id,
        )

        # Переносим semantic_groups из текущего asset,
        # отфильтровав группы с несуществующими узлами
        if self._current_asset is not None:
            valid_ids = list(asset.geometry.get("node_ids", []))
            asset.semantic_groups = self._prune_groups(
                self._current_asset.semantic_groups,
                valid_ids,
            )
            # Копируем параметры целиком + чистим таргеты
            # на удалённые (после prune_groups) группы
            asset.parameters = dict(self._current_asset.parameters)
            asset.prune_parameters()

        try:
            save_asset(asset)
        except StorageError as e:
            QMessageBox.critical(
                self, "Ошибка сохранения",
                f"Не удалось сохранить:\n\n{e}"
            )
            return

        # Обновляем current_asset
        self._current_asset = asset
        self._groups_panel.set_asset(asset)
        self._parameters_panel.set_asset(asset)

        self._mark_saved()
        self._browser.refresh()
        self.statusBar().showMessage(
            f"Сохранено: {asset.name}", 2000
        )

    def _on_save_as(self) -> None:
        dlg = SaveAssetDialog(
            default_name=self._current_asset_name or "Новый ассет",
            parent=self,
        )
        if dlg.exec() != SaveAssetDialog.DialogCode.Accepted:
            return

        # Контура может не быть — тогда сохраняем «пустой» Asset
        # (например, чтобы сразу привязать подложку).
        if self._contour_item is not None:
            contour = self._contour_item.contour
        else:
            contour = VectorContour(points=[])

        asset = Asset.from_contour(
            contour,
            name=dlg.result_name,
            type_=dlg.result_type,
        )

        # Save As копирует группы из текущего asset (отфильтрованные)
        if self._current_asset is not None:
            valid_ids = list(asset.geometry.get("node_ids", []))
            asset.semantic_groups = self._prune_groups(
                self._current_asset.semantic_groups,
                valid_ids,
            )
            asset.parameters = dict(self._current_asset.parameters)
            asset.prune_parameters()

            # Подложка: скопировать PNG под новым asset_id
            old_ref = self._current_asset.reference_image
            if old_ref is not None and old_ref.is_valid():
                old_path = get_reference_image_path(old_ref.filename)
                if old_path.exists() and old_path.parent == old_path.parent:
                    try:
                        new_filename = f"{asset.id}_ref.png"
                        new_path = get_reference_image_path(new_filename)
                        new_path.write_bytes(old_path.read_bytes())

                        new_ref = ReferenceImage.from_dict(
                            old_ref.to_dict()
                        )
                        new_ref.filename = new_filename
                        asset.reference_image = new_ref
                    except OSError:
                        # Не смогли скопировать — оставляем как было
                        asset.reference_image = old_ref

        try:
            save_asset(asset)
        except StorageError as e:
            QMessageBox.critical(
                self, "Ошибка сохранения",
                f"Не удалось сохранить:\n\n{e}"
            )
            return

        self._current_asset = asset
        self._current_asset_id = asset.id
        self._current_asset_name = asset.name
        self._current_asset_type = asset.type

        self._groups_panel.set_asset(asset)
        self._parameters_panel.set_asset(asset)

        self._mark_saved()
        self._browser.refresh()
        self.statusBar().showMessage(
            f"Создан новый Asset: {asset.name}", 3000
        )

    # ============================================================
    # EXTRA EDGES (V8-lite)
    # ============================================================

    def _on_add_extra_edge(self) -> None:
        """Соединить два выделенных узла дополнительным ребром."""
        if self._contour_item is None:
            self.statusBar().showMessage(
                "Сначала создайте или откройте контур", 3000,
            )
            return

        nodes = [
            it for it in self._scene.selectedItems()
            if isinstance(it, NodeItem)
        ]

        if len(nodes) != 2:
            self.statusBar().showMessage(
                "Выберите ровно ДВА узла через Ctrl+клик, затем Ctrl+J",
                5000,
            )
            return

        a_id = nodes[0].node_id
        b_id = nodes[1].node_id

        if not a_id or not b_id:
            self.statusBar().showMessage(
                "У одного из узлов нет node_id", 3000,
            )
            return

        contour = self._contour_item.contour
        extra_snapshot = list(contour.extra_edges)

        if not contour.add_extra_edge(a_id, b_id):
            self.statusBar().showMessage(
                "Такое extra-ребро уже существует "
                "или узлы недействительны", 3500,
            )
            return

        self._contour_item._selected_extra = None
        self._contour_item._selected_edge_idx = None
        self._contour_item.update()

        self._undo_stack.append(
            (
                self._contour_item,
                list(contour.points),
                "extra_edges",
                extra_snapshot,
            )
        )

        self._mark_modified()
        self.statusBar().showMessage(
            f"Extra создано: {a_id} ↔ {b_id}", 2500,
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

        entry = self._undo_stack.pop()
        item = entry[0]
        snapshot = entry[1]

        # -------- EXTRA EDGES ----------------
        if (
            len(entry) >= 4
            and isinstance(entry[2], str)
            and entry[2] == "extra_edges"
        ):
            item.contour.points = list(snapshot)
            item.contour.extra_edges = [
                tuple(e) for e in entry[3]
            ]

            item._selected_edge_idx = None
            item._selected_extra = None
            item._hover_edge_idx = None
            item._hover_extra = None

            item._rebuild_nodes()
            item._rebuild_path()
            item.update()

        # -------- PARAMETER ------------------
        elif len(entry) >= 4:
            item.contour.points = list(snapshot)
            item._selected_edge_idx = None
            item._selected_extra = None
            item._rebuild_nodes()
            item._rebuild_path()

            param_id = entry[2]
            old_value = entry[3]
            if self._current_asset is not None:
                p = self._current_asset.get_parameter(param_id)
                if p is not None:
                    p.value = old_value
                    self._parameters_panel.refresh()

        # -------- ОБЫЧНЫЙ --------------------
        else:
            item.contour.points = list(snapshot)
            item._selected_edge_idx = None
            item._selected_extra = None
            item._rebuild_nodes()
            item._rebuild_path()

        self._reset_param_undo_session()
        self._mark_modified()
        self.statusBar().showMessage("Отменено", 2000)

    # ============================================================
    # KEYBOARD
    # ============================================================

    # ============================================================
    # EVENT FILTER — клик по пустому месту сцены
    # ============================================================

    def eventFilter(self, obj, event) -> bool:
        if obj is self._scene:
            if event.type() == QEvent.Type.GraphicsSceneMousePress:
                # Сбрасываем edge-подсветку ВСЕГДА при клике.
                # Если клик попадёт в грань — ContourItem сам её
                # поставит заново. Если мимо — останется сброшено.
                if self._contour_item is not None:
                    self._contour_item._selected_edge_idx = None
                    self._contour_item._selected_extra = None
                    self._contour_item._hover_edge_idx = None
                    self._contour_item._hover_extra = None
                    self._contour_item.update()

                pos = event.scenePos()
                items = self._scene.items(pos)
                has_node = any(
                    isinstance(it, NodeItem) for it in items
                )

                if has_node:
                    return False

                if not has_node:
                    near_edge = False

                    if self._contour_item is not None:
                        # Extra — приоритет
                        try:
                            extra = (
                                self._contour_item
                                ._find_extra_edge_at(
                                    pos.x(), pos.y(),
                                )
                            )
                            near_edge = extra is not None
                        except Exception:
                            near_edge = False

                        # Main — только если extra нет
                        if not near_edge:
                            try:
                                idx = (
                                    self._contour_item
                                    ._find_edge_at(
                                        pos.x(), pos.y(),
                                    )
                                )
                                near_edge = idx is not None
                            except Exception:
                                near_edge = False

                    # Если клик не в узел/ребро — сброс.
                    # Если попал в ребро — тоже сбрасываем текущую
                    # грань, чтобы клик в другое место не оставлял
                    # старую синюю подсветку.
                    self._on_empty_scene_click()
                    if not near_edge:
                        return True
                    # Если попали в ребро — не съедаем событие,
                    # пусть ContourItem сам поставит новую грань.
                    return False

        return super().eventFilter(obj, event)

    def _on_empty_scene_click(self) -> None:
        """Клик мимо узлов и граней:
        - снимаем подсветку групп/параметров
        - сбрасываем выделение ВСЕХ items на сцене
        - сбрасываем выбранную грань (для extrude) и hover-грань
        """
        if self._contour_item is not None:
            self._contour_item.clear_highlight()
            self._contour_item._selected_edge_idx = None
            self._contour_item._selected_extra = None
            self._contour_item._hover_edge_idx = None
            self._contour_item._hover_extra = None
            self._contour_item.update()

        self._scene.clearSelection()
        self._scene.update()

        self._groups_panel.clear_selection()
        self._parameters_panel.clear_selection()

    def keyPressEvent(self, event) -> None:
        # Ctrl+A — выделить все узлы
        if event.matches(QKeySequence.StandardKey.SelectAll):
            if self._contour_item is not None:
                for node in self._contour_item._nodes:
                    node.setSelected(True)
                event.accept()
                return

        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self._delete_selected_nodes():
                event.accept()
                return

        super().keyPressEvent(event)

    def _delete_selected_nodes(self) -> bool:
        """Удалить выделенное: extra_edge ИЛИ узлы.

        - Если выделена extra_edge — удалить только её.
        - Иначе — существующая логика для узлов:
            выделены ВСЕ → удалить весь контур (с подтверждением).
            останется < 3 → предупреждение.
            иначе — массовое удаление + одна undo-запись.
        """
        if self._contour_item is None:
            return False

        # ---- EXTRA EDGE ----------------------------------------
        item = self._contour_item
        extra = getattr(item, "_selected_extra", None)
        if extra is not None:
            a_id, b_id = extra
            snapshot = list(item.contour.extra_edges)

            if item.contour.remove_extra_edge(a_id, b_id):
                item._selected_extra = None
                item._hover_extra = None
                item.update()

                self._undo_stack.append(
                    (
                        item,
                        list(item.contour.points),
                        "extra_edges",
                        snapshot,
                    )
                )
                self._mark_modified()
                self.statusBar().showMessage(
                    f"Extra удалено: {a_id} — {b_id}", 2500,
                )
                return True

        # ---- NODES ---------------------------------------------
        selected = [
            it for it in self._scene.selectedItems()
            if isinstance(it, NodeItem)
        ]
        if not selected:
            return False

        item = self._contour_item
        n_total = len(item.contour.points)
        n_del = len(selected)

        # Все узлы → удалить контур целиком
        if n_del == n_total:
            reply = QMessageBox.question(
                self, "Удалить контур",
                f"Выделены все {n_total} узлов.\n\n"
                f"Удалить весь контур?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return True

            self._remove_contour_only()
            self._mark_modified()
            self.statusBar().showMessage("Контур удалён", 2000)
            return True

        # Проверка минимума
        n_remaining = n_total - n_del
        if n_remaining < 3:
            self.statusBar().showMessage(
                f"Нельзя удалить: останется {n_remaining}, "
                f"минимум 3.", 3000,
            )
            return True

        # Undo snapshot
        snapshot = list(item.contour.points)

        # Индексы выделенных
        indices = sorted(
            {node.idx for node in selected},
            reverse=True,
        )

        # Удалять с конца, чтобы индексы не сдвигались
        for idx in indices:
            item.contour.remove_point(idx)

        item._selected_edge_idx = None
        item._rebuild_nodes()
        item._rebuild_path()

        self._undo_stack.append((item, snapshot))
        self._mark_modified()
        self.statusBar().showMessage(
            f"Удалено узлов: {n_del}", 2000,
        )
        return True

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
