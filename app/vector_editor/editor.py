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
    QSizePolicy,
    QPushButton,
    QWidget,
    QFileDialog,
    QLabel,
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
from .view.scale_dialog import ScaleDialog
from .model.auto_rule import recalculate_auto_points
from .view.semantic_groups_panel import SemanticGroupsPanel
from .view.arc_dialog import ArcDialog
from .view.parameters_panel import ParametersPanel
from .view.stretch_dialog import StretchDialog
from .model.parameter import (
    compute_delta_for_parameter,
    apply_delta_to_points,
)
from .view.save_asset_dialog import SaveAssetDialog
from .view.items.contour_item import ContourItem
from .view.items.node_item import NodeItem
from .view.items.extra_node_item import ExtraNodeItem
from .view.items.reference_item import ReferenceImageItem
from .view.reference_properties_dialog import ReferencePropertiesDialog
from .model.reference_image import ReferenceImage


EXTRUDE_TEST_DISTANCE = 2.0


def _parse_arcs(raw) -> dict:
    """Разобрать arcs из JSON: [[a, b, bulge], ...]."""
    result = {}
    if not isinstance(raw, list):
        return result
    for item in raw:
        if not isinstance(item, (list, tuple)) or len(item) != 3:
            continue
        a, b, v = item
        if not isinstance(a, str) or not isinstance(b, str):
            continue
        if a == b:
            continue
        try:
            bulge = float(v)
        except (TypeError, ValueError):
            continue
        if abs(bulge) < 1e-9:
            continue
        result[(a, b)] = bulge
    return result


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
        self._redo_stack: list[tuple] = []
        self._in_undo_redo: bool = False

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
        self._setup_shortcuts()
        self._update_title()

        self.statusBar().showMessage(
            "Ctrl+N — новый · Ctrl+S — сохранить · "
            "Ctrl+Shift+S — сохранить как · Ctrl+E — extrude"
        )

    # ============================================================
    # UI
    # ============================================================

    def _setup_shortcuts(self) -> None:
        """Глобальные горячие клавиши окна."""
        from PySide6.QtGui import QShortcut, QKeySequence

        # Ctrl+Z уже привязан в меню (Undo). Здесь только redo.
        QShortcut(
            QKeySequence("Ctrl+Shift+Z"), self,
            activated=self._on_redo,
        )
        QShortcut(
            QKeySequence("Ctrl+Y"), self,
            activated=self._on_redo,
        )

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
        # V9-A1: показ размера bbox в метрах
        self._size_label = QLabel("")
        self._size_label.setStyleSheet(
            "color: #888; padding-right: 12px;"
        )
        self.statusBar().addPermanentWidget(self._size_label)

        # V16: координаты выделенного узла(ов)
        self._coord_label = QLabel("")
        self._coord_label.setStyleSheet(
            "color: #0066CC; padding-right: 12px; "
            "font-weight: 600;"
        )
        self.statusBar().addPermanentWidget(self._coord_label)


    def _build_toolbar(self) -> None:
        tb = QToolBar("Main", self)
        tb.setMovable(False)
        self.addToolBar(tb)
        self._toolbar = tb

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

        # V9c: режим "точка" — клик по сцене создаёт extra-точку
        self._act_point = QAction("📍 Точка", self)
        self._act_point.setCheckable(True)
        self._act_point.setToolTip(
            "Клик по сцене — поставить extra-точку "
            "(шаблон для auto_rule). Esc — выйти."
        )
        self._act_point.toggled.connect(self._on_point_mode_toggled)
        tb.addAction(self._act_point)

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

        tb.addSeparator()

        act_draw = QAction("✏ Рисовать", self)
        act_draw.setShortcut(QKeySequence("D"))
        act_draw.setShortcutContext(
            Qt.ShortcutContext.ApplicationShortcut
        )
        act_draw.setToolTip(
            "Начать рисовать контур (D). "
            "Клик — точка, Enter — замкнуть, Esc — отмена."
        )
        act_draw.triggered.connect(self._on_start_draw)
        tb.addAction(act_draw)

        act_validate = QAction("🔍 Проверить", self)
        act_validate.setShortcut(QKeySequence("Ctrl+Shift+V"))
        act_validate.setShortcutContext(
            Qt.ShortcutContext.ApplicationShortcut
        )
        act_validate.setToolTip(
            "Проверить инварианты контура (Ctrl+Shift+V)"
        )
        act_validate.triggered.connect(self._on_validate_contour)
        tb.addAction(act_validate)

        # Второй тулбар — на отдельной строке (всегда видна)
        tb2 = QToolBar("Edit", self)
        tb2.setMovable(False)
        self.addToolBarBreak()
        self.addToolBar(tb2)
        self._toolbar2 = tb2

        act_stretch = QAction("📏 Растяжка", self)
        act_stretch.setToolTip(
            "Создать параметр-растяжение (высоту) между "
            "низом и верхом"
        )
        act_stretch.triggered.connect(self._on_stretch)
        tb2.addAction(act_stretch)

        act_arc = QAction("🎯 Изогнуть", self)
        act_arc.setToolTip(
            "Изогнуть выделенное ребро (или ПКМ по ребру)"
        )
        act_arc.triggered.connect(self._on_arc_clicked)
        tb2.addAction(act_arc)

        tb.addSeparator()

        act_align_x = QAction("⇔ X", self)
        act_align_x.setToolTip(
            "Выровнять выделенные узлы по среднему X"
        )
        act_align_x.triggered.connect(self._align_x)
        tb2.addAction(act_align_x)

        act_align_y = QAction("⇕ Y", self)
        act_align_y.setToolTip(
            "Выровнять выделенные узлы по среднему Y"
        )
        act_align_y.triggered.connect(self._align_y)
        tb2.addAction(act_align_y)

        act_dist_x = QAction("⇹ X", self)
        act_dist_x.setToolTip(
            "Равномерно распределить 3+ узла по X"
        )
        act_dist_x.triggered.connect(self._distribute_x)
        tb2.addAction(act_dist_x)

        act_dist_y = QAction("⇳ Y", self)
        act_dist_y.setToolTip(
            "Равномерно распределить 3+ узла по Y"
        )
        act_dist_y.triggered.connect(self._distribute_y)
        tb2.addAction(act_dist_y)

        tb.addSeparator()

        act_scale = QAction("📐 Масштаб", self)
        act_scale.setToolTip(
            "Пропорционально масштабировать контур до заданного размера"
        )
        act_scale.triggered.connect(self._on_scale_clicked)
        tb2.addAction(act_scale)

        # Список «дополнительных» actions — их можно скрывать
        self._extra_actions = [
            act_stretch,
            act_arc,
            act_align_x,
            act_align_y,
            act_dist_x,
            act_dist_y,
            act_scale,
        ]

    def _on_arc_clicked(self) -> None:
        """Изогнуть выделенное ребро (main или extra)."""
        if self._contour_item is None:
            self.statusBar().showMessage(
                "Сначала открой ассет", 3000,
            )
            return

        item = self._contour_item
        contour = item.contour

        edge_idx = item.selected_edge_idx
        extra = item.selected_extra()

        if edge_idx is None and extra is None:
            self.statusBar().showMessage(
                "Кликни по грани контура (линия), потом Изогнуть",
                4000,
            )
            return

        if extra is not None:
            a_id, b_id = extra
        else:
            n = len(contour.points)
            if not (0 <= edge_idx < n):
                return
            ids = contour.node_ids
            a_id = ids[edge_idx] if edge_idx < len(ids) else None
            b_id = ids[(edge_idx + 1) % n] if (edge_idx + 1) % n < len(ids) else None
            if a_id is None or b_id is None:
                return

        current = contour.get_arc(a_id, b_id)

        dlg = ArcDialog(current, self)

        def on_changed(v):
            contour.set_arc(a_id, b_id, v)
            item._rebuild_path()

        dlg.value_changed.connect(on_changed)

        result = dlg.exec()

        if result != ArcDialog.DialogCode.Accepted:
            contour.set_arc(a_id, b_id, current)
            item._rebuild_path()
            return

        final = dlg.value()
        contour.set_arc(a_id, b_id, final)
        item._rebuild_path()

        self.statusBar().showMessage(
            f"Изогнуто: {final:+.2f}", 3000,
        )

    def _connect_signals(self) -> None:
        self._canvas.contour_created.connect(self._on_contour_created)
        self._canvas.empty_click.connect(self._on_empty_scene_click)
        self._canvas.rubber_band_finished.connect(
            self._on_rubber_band_finished
        )
        self._canvas.extrude_click.connect(self._on_extrude_click)
        self._canvas.point_click.connect(self._on_point_click)
        self._canvas.extrude_finished.connect(
            self._on_extrude_finished
        )
        self._browser.asset_open_requested.connect(self._on_open_asset)
        self._browser.asset_delete_requested.connect(
            self._on_delete_asset
        )
        self._browser.asset_rename_requested.connect(
            self._on_rename_asset
        )

        # Клик по пустому месту сцены — снимаем подсветку группы
        self._scene.installEventFilter(self)

        self._scene.selectionChanged.connect(
            self._on_scene_selection_changed
        )
        # V16: координаты выделенного узла
        self._scene.selectionChanged.connect(
            self._update_node_coords
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
        print(f"[MODIFIED] undo_stack={len(self._undo_stack)}")

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
        """Обновить список выделенных node_ids в панели групп.

        Учитывает и main (NodeItem), и extra (ExtraNodeItem).
        """
        node_ids = []
        for it in self._scene.selectedItems():
            if isinstance(it, (NodeItem, ExtraNodeItem)):
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
            snapshot = self._contour_item.contour.snapshot()
            self._record_undo(
                (self._contour_item, snapshot, param_id, old_value)
            )
            self._param_undo_active_id = param_id
            self._param_undo_timer.restart()

        # --- Применяем сдвиг ---
        node_delta = compute_delta_for_parameter(
            param, delta_value, self._current_asset.semantic_groups,
        )

        if node_delta:
            c = self._contour_item.contour

            # Main узлы
            new_points = apply_delta_to_points(
                c.points, c.node_ids, node_delta,
            )
            c.points = new_points

            # Extra-узлы (e_*) — тоже
            if c.extra_points:
                new_extra = apply_delta_to_points(
                    c.extra_points, c.extra_node_ids, node_delta,
                )
                c.extra_points = new_extra

            self._contour_item._rebuild_nodes()
            self._contour_item._rebuild_extra_nodes()
            self._contour_item._rebuild_path()

            # V9b: пересчёт авто-точек после сдвига
            self._recalc_auto_points()

        param.value = new_value
        self._mark_modified()

    def _recalc_auto_points(self) -> None:
        """V9b: пересчитать авто-точки после изменения модели."""
        if self._current_asset is None or self._contour_item is None:
            return
        added = recalculate_auto_points(
            self._contour_item.contour,
            self._current_asset.semantic_groups,
        )
        if added > 0:
            self._contour_item._rebuild_extra_nodes()
            self._contour_item._rebuild_path()

    def _on_point_mode_toggled(self, checked: bool) -> None:
        """Переключить режим "📍 Точка"."""
        if self._canvas is None:
            return
        if checked:
            self._canvas.set_tool("point")
        else:
            self._canvas.set_tool("select")

    def _on_point_click(self, x: float, y: float) -> None:
        """V9c: создать extra-точку по клику на сцене."""
        if self._contour_item is None:
            return

        # A-доп: снапшот ДО добавления — чтобы Ctrl+Z убирал точку
        self._push_contour_snapshot()

        c = self._contour_item.contour
        try:
            c.add_extra_point(float(x), float(y))
        except Exception as e:
            self.statusBar().showMessage(
                f"Не удалось создать точку: {e}", 3000,
            )
            return
        self._contour_item._rebuild_extra_nodes()
        self._contour_item._rebuild_path()
        self._mark_modified()
        self.statusBar().showMessage(
            "Точка добавлена. Выдели её и создай группу "
            "(+ в панели Группы).", 4000,
        )

    def _on_groups_changed(self) -> None:
        """Пользователь изменил группы — отметить Asset как изменённый."""
        self._recalc_auto_points()
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
        self._redo_stack.clear()

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

        self._record_undo((item, snapshot))

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

    def _on_start_draw(self) -> None:
        """Включить draw-режим. Работает в любой момент."""
        if self._contour_item is not None:
            reply = QMessageBox.question(
                self, "Новый контур",
                "На сцене уже есть контур.\n\n"
                "Очистить его и начать рисовать заново?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            # Очищаем контур, но Asset и подложку не трогаем
            self._contour_item.contour.points = []
            self._contour_item.contour.node_ids = []
            self._contour_item.contour.extra_edges = []
            self._contour_item.contour.extra_points = []
            self._contour_item.contour.extra_node_ids = []
            self._contour_item._rebuild_nodes()
            self._contour_item._rebuild_extra_nodes()
            self._contour_item._rebuild_path()

        self._canvas.set_tool("draw")
        if self._reference_item is not None:
            self._reference_item.set_interactive(False)

        self.statusBar().showMessage(
            "Рисование: ЛКМ — точка · Enter — замкнуть · Esc — отмена",
            8000,
        )

    def _on_new(self) -> None:
        if not self._confirm_discard():
            return

        # Спрашиваем имя + тип СРАЗУ, до рисования
        dlg = SaveAssetDialog(
            default_name="Новый",
            parent=self,
        )
        if dlg.exec() != SaveAssetDialog.DialogCode.Accepted:
            return

        # Создаём пустой Asset (без точек) и сразу сохраняем
        empty_contour = VectorContour(points=[])
        asset = Asset.from_contour(
            empty_contour,
            name=dlg.result_name,
            type_=dlg.result_type,
        )

        try:
            save_asset(asset)
        except StorageError as e:
            QMessageBox.critical(
                self, "Ошибка создания",
                f"Не удалось создать Asset:\n\n{e}"
            )
            return

        # Открываем его в редакторе — контур пустой
        self._load_asset_into_editor(asset)
        self._browser.refresh()

        # Входим в draw — рисуй
        self._canvas.set_tool("draw")
        if self._reference_item is not None:
            self._reference_item.set_interactive(False)

        self.statusBar().showMessage(
            f"Asset «{asset.name}» создан. "
            f"Нарисуйте контур: ЛКМ — точка · "
            f"Enter — замкнуть · Esc — отмена", 8000
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
        self._redo_stack.clear()

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
        self._check_contour_invariants("после изменения")

    def _check_contour_invariants(self, tag: str = "") -> bool:
        """Проверить инварианты. Печатает проблемы в консоль.

        Возвращает True если всё ок.
        Побочно обновляет размер в статусбаре.
        """
        self._update_size_display()
        if self._contour_item is None:
            return True

        problems = self._contour_item.contour.validate()
        if not problems:
            if tag:
                print(f"[OK] {tag}: контур валиден")
            return True

        print(f"[!!] {tag}: НАЙДЕНЫ ПРОБЛЕМЫ ({len(problems)}):")
        for p in problems:
            print(f"     - {p}")

        self.statusBar().showMessage(
            f"⚠ Проблема контура ({len(problems)}). "
            f"Ctrl+Shift+V — детали", 6000,
        )
        return False

    def _on_validate_contour(self) -> None:
        """Ctrl+Shift+V — принудительная проверка."""
        if self._contour_item is None:
            QMessageBox.information(
                self, "Проверка контура",
                "Нет контура на сцене.",
            )
            return

        c = self._contour_item.contour
        problems = c.validate()

        info = [
            f"points: {len(c.points)}",
            f"node_ids: {len(c.node_ids)}",
            f"extra_points: {len(c.extra_points)}",
            f"extra_node_ids: {len(c.extra_node_ids)}",
            f"extra_edges: {len(c.extra_edges)}",
            f"undo_stack: {len(self._undo_stack)}",
            "",
        ]

        if not problems:
            info.append("✓ Все инварианты в порядке")
        else:
            info.append(f"⚠ Проблем: {len(problems)}")
            for p in problems[:20]:
                info.append(f"  - {p}")

        QMessageBox.information(
            self, "Проверка контура",
            "\n".join(info),
        )
        print("\n".join(info))

    def _on_node_drag_started(self) -> None:
        """Пользователь начал тянуть узел — запомним снапшот."""
        if self._contour_item is None:
            return
        self._pending_drag_snapshot = (
            self._contour_item.contour.snapshot()
        )

    def _on_node_drag_finished(self) -> None:
        """Пользователь отпустил узел — если что-то изменилось,
        кладём ОДНУ undo-запись.
        """
        snapshot = self._pending_drag_snapshot
        self._pending_drag_snapshot = None

        if snapshot is None or self._contour_item is None:
            return

        current = self._contour_item.contour.snapshot()
        if current == snapshot:
            return

        self._record_undo((self._contour_item, snapshot))

    # ============================================================
    # OPEN
    # ============================================================

    def _on_rename_asset(self, asset_id: str) -> None:
        """Переименовать Asset через диалог."""
        # Загружаем asset
        try:
            asset = load_asset(self._browser_asset_path(asset_id))
        except StorageError as e:
            QMessageBox.warning(
                self, "Ошибка загрузки",
                f"Не удалось загрузить Asset:\n\n{e}"
            )
            return

        # Диалог ввода
        from PySide6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(
            self, "Переименовать",
            f"Новое имя для «{asset.name}»:",
            text=asset.name,
        )
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name or new_name == asset.name:
            return

        # Сохраняем с новым именем
        asset.name = new_name
        try:
            save_asset(asset)
        except StorageError as e:
            QMessageBox.critical(
                self, "Ошибка сохранения",
                f"Не удалось сохранить:\n\n{e}"
            )
            return

        # Если это текущий открытый Asset — обновляем заголовок
        if asset_id == self._current_asset_id:
            self._current_asset_name = new_name
            self._mark_saved()
            self._update_title()

        self._browser.refresh()
        self.statusBar().showMessage(
            f"Asset переименован: {new_name}", 2000,
        )

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
            extra_points=[
                (float(p[0]), float(p[1]))
                for p in geometry.get("extra_points", [])
                if isinstance(p, (list, tuple)) and len(p) >= 2
            ],
            extra_node_ids=list(
                geometry.get("extra_node_ids", [])
            ),
            arcs=_parse_arcs(geometry.get("arcs")),
        )

        # Автоочистка: если старый JSON битый (дубли, висящие
        # extra_edges) — починить
        # Собрать id всех групп — чтобы sanitize не убил
        # extra-точки, которые в них (якоря, слоты)
        _keep = set()
        for g in asset.semantic_groups.values():
            _keep.update(g.node_ids)
        fixes = contour.sanitize(keep_extra_ids=_keep)
        if fixes > 0:
            print(f"[SANITIZE] исправлено проблем: {fixes}")
            self.statusBar().showMessage(
                f"Asset почищен при загрузке ({fixes} правок)",
                5000,
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
        self._update_size_display()

        # Подложка (если есть в Asset'е)
        self._rebuild_reference_item()
        if self._reference_item is not None:
            self._reference_item.set_interactive(True)

        self._mark_saved()

        self._canvas.set_tool("select")
        self._scene.clearSelection()

        # V-A: авто-zoom под контур при открытии.
        # QTimer — чтобы layout окна успел применить размеры viewport.
        from PySide6.QtCore import QTimer as _QT
        _QT.singleShot(0, self._fit_to_contour)

        self.statusBar().showMessage(
            f"Открыт: {asset.name} ({asset.type})", 4000
        )

    def _fit_to_contour(self) -> None:
        """V-A: подогнать вид canvas под bbox текущего контура."""
        if self._contour_item is None or self._canvas is None:
            return
        c = self._contour_item.contour
        pts = list(c.points) + list(c.extra_points)
        if not pts:
            return

        xs = [float(p[0]) for p in pts]
        ys = [float(p[1]) for p in pts]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)

        # Совсем маленький объект — минимум 0.5 м, чтобы не зумиться
        # до бесконечности.
        if (x1 - x0) < 0.5 and (y1 - y0) < 0.5:
            cx = (x0 + x1) / 2
            cy = (y0 + y1) / 2
            x0, x1 = cx - 0.25, cx + 0.25
            y0, y1 = cy - 0.25, cy + 0.25

        self._canvas.fit_to_rect(x0, y0, x1, y1)

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
            group_ids = set()
            if self._current_asset is not None:
                for g in self._current_asset.semantic_groups.values():
                    group_ids.update(g.node_ids)
            contour.sanitize(keep_extra_ids=group_ids)
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
            valid_ids = (
                list(asset.geometry.get("node_ids", []))
                + list(asset.geometry.get("extra_node_ids", []))
            )
            asset.semantic_groups = self._prune_groups(
                self._current_asset.semantic_groups,
                valid_ids,
            )
            # Копируем параметры целиком + чистим таргеты
            # на удалённые (после prune_groups) группы
            asset.parameters = dict(self._current_asset.parameters)
            asset.prune_parameters()

            # Копируем подложку — иначе она теряется при Save
            asset.reference_image = self._current_asset.reference_image

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
            group_ids = set()
            if self._current_asset is not None:
                for g in self._current_asset.semantic_groups.values():
                    group_ids.update(g.node_ids)
            contour.sanitize(keep_extra_ids=group_ids)
        else:
            contour = VectorContour(points=[])

        asset = Asset.from_contour(
            contour,
            name=dlg.result_name,
            type_=dlg.result_type,
        )

        # Save As копирует группы из текущего asset (отфильтрованные)
        if self._current_asset is not None:
            valid_ids = (
                list(asset.geometry.get("node_ids", []))
                + list(asset.geometry.get("extra_node_ids", []))
            )
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
    # STRETCH (V9a) — параметр-растяжение
    # ============================================================

    def _on_stretch(self) -> None:
        """Мастер параметра растяжения."""
        if self._current_asset is None:
            self.statusBar().showMessage(
                "Сначала откройте Asset", 3000,
            )
            return

        if not self._current_asset.semantic_groups:
            self.statusBar().showMessage(
                "Создайте группы (foundation, top) сначала", 4000,
            )
            return

        dlg = StretchDialog(self._current_asset, self)
        if dlg.exec() != StretchDialog.DialogCode.Accepted:
            return

        # Готовим targets
        from .model.parameter import Parameter, ParameterTarget

        # Ось → (kx_top, ky_top, kx_mid, ky_mid, kx_second, ky_second)
        axis = dlg.result_axis
        if axis == "y":
            kx_t, ky_t = 0.0, 1.0
            kx_m, ky_m = 0.0, 0.5
            kx_s, ky_s = 0.0, -1.0
        elif axis == "x+1":
            kx_t, ky_t = 1.0, 0.0
            kx_m, ky_m = 0.5, 0.0
            kx_s, ky_s = -1.0, 0.0
        else:  # "x-1"
            kx_t, ky_t = -1.0, 0.0
            kx_m, ky_m = -0.5, 0.0
            kx_s, ky_s = 1.0, 0.0

        targets: list = []

        # Тянется — едет на всю Δ
        targets.append(ParameterTarget(
            dlg.result_top_id, koef_x=kx_t, koef_y=ky_t,
        ))

        # Вторая сторона — едет на -Δ
        if dlg.result_second_id:
            targets.append(ParameterTarget(
                dlg.result_second_id, koef_x=kx_s, koef_y=ky_s,
            ))

        # Середина — едет на Δ/2
        if dlg.result_middle_id:
            targets.append(ParameterTarget(
                dlg.result_middle_id, koef_x=kx_m, koef_y=ky_m,
            ))

        # Стоит — НЕ в targets

        param = Parameter(
            name=dlg.result_name,
            label=dlg.result_label,
            value=0.0,
            unit="м",
            targets=targets,
        )
        self._current_asset.add_parameter(param)

        # Обновляем панель
        self._parameters_panel.set_asset(self._current_asset)
        self._mark_modified()

        self.statusBar().showMessage(
            f"Параметр растяжения создан: {param.label}. "
            f"Откройте панель «Параметры» справа, "
            f"тяните значение.",
            6000,
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
            if isinstance(it, (NodeItem, ExtraNodeItem))
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
        snapshot = contour.snapshot()

        if not contour.add_extra_edge(a_id, b_id):
            self.statusBar().showMessage(
                "Такое extra-ребро уже существует "
                "или узлы недействительны", 3500,
            )
            return

        self._contour_item._selected_extra = None
        self._contour_item._selected_edge_idx = None
        self._contour_item.update()

        self._record_undo(
            (self._contour_item, snapshot)
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

        snapshot = item.contour.snapshot()

        ok = item.extrude_selected_face(EXTRUDE_TEST_DISTANCE)
        if not ok:
            self.statusBar().showMessage(
                "Не удалось вытянуть грань", 3000
            )
            return

        self._record_undo((item, snapshot))
        self._mark_modified()
        self.statusBar().showMessage(
            f"Extrude на {EXTRUDE_TEST_DISTANCE} м", 2000
        )

    # ============================================================
    # UNDO
    # ============================================================

    def _get_selected_nodes(self) -> list:
        """V-A1: вернуть выделенные узлы (main + extra).

        Формат: список (kind, ref, x, y) где
          kind = "main"  → ref = idx (int)
          kind = "extra" → ref = node_id (str)
        """
        from .view.items.node_item import NodeItem
        from .view.items.extra_node_item import ExtraNodeItem

        contour = self._contour_item.contour if self._contour_item else None
        if contour is None:
            return []

        items = []
        for it in self._scene.selectedItems():
            if isinstance(it, NodeItem):
                idx = it.idx
                if 0 <= idx < len(contour.points):
                    x, y = contour.points[idx]
                    items.append(("main", idx, x, y))
            elif isinstance(it, ExtraNodeItem):
                nid = it.node_id
                if nid in contour.extra_node_ids:
                    i = contour.extra_node_ids.index(nid)
                    x, y = contour.extra_points[i]
                    items.append(("extra", nid, x, y))
        return items

    def _apply_node_position(self, kind: str, ref, x: float, y: float) -> None:
        """Записать новую позицию в contour (main или extra)."""
        contour = self._contour_item.contour
        if kind == "main":
            contour.set_point(int(ref), x, y)
        else:
            contour.set_point_by_id(str(ref), x, y)

    def _record_undo(self, entry) -> None:
        """Push в undo-стек. Новое действие очищает redo."""
        if not self._in_undo_redo:
            self._redo_stack.clear()
        self._undo_stack.append(entry)

    def _push_contour_snapshot(self) -> None:
        """Сохранить snapshot для undo."""
        if self._contour_item is None:
            return
        snapshot = self._contour_item.contour.snapshot()
        self._record_undo((self._contour_item, snapshot))

    def _align_x(self) -> None:
        """Выровнять выделенные узлы (main + extra) по среднему X."""
        items = self._get_selected_nodes()
        if len(items) < 2:
            self.statusBar().showMessage(
                "Выдели 2+ узла для выравнивания", 3000,
            )
            return

        avg_x = sum(x for _, _, x, _ in items) / len(items)

        self._push_contour_snapshot()
        for kind, ref, _, y in items:
            self._apply_node_position(kind, ref, avg_x, y)

        self._contour_item._rebuild_nodes()
        self._contour_item._rebuild_extra_nodes()
        self._contour_item._rebuild_path()
        self._mark_modified()
        self.statusBar().showMessage(
            f"Выровнено по X ({len(items)} узлов)", 2000,
        )

    def _align_y(self) -> None:
        """Выровнять выделенные узлы (main + extra) по среднему Y."""
        items = self._get_selected_nodes()
        if len(items) < 2:
            self.statusBar().showMessage(
                "Выдели 2+ узла для выравнивания", 3000,
            )
            return

        avg_y = sum(y for _, _, _, y in items) / len(items)

        self._push_contour_snapshot()
        for kind, ref, x, _ in items:
            self._apply_node_position(kind, ref, x, avg_y)

        self._contour_item._rebuild_nodes()
        self._contour_item._rebuild_extra_nodes()
        self._contour_item._rebuild_path()
        self._mark_modified()
        self.statusBar().showMessage(
            f"Выровнено по Y ({len(items)} узлов)", 2000,
        )

    def _distribute_x(self) -> None:
        """Равномерно распределить узлы (main + extra) по X."""
        items = self._get_selected_nodes()
        if len(items) < 3:
            self.statusBar().showMessage(
                "Выдели 3+ узла для распределения", 3000,
            )
            return

        items_sorted = sorted(items, key=lambda t: t[2])
        xs = [x for _, _, x, _ in items_sorted]
        x_min, x_max = xs[0], xs[-1]
        n = len(items_sorted)
        step = (x_max - x_min) / (n - 1)

        self._push_contour_snapshot()
        for i, (kind, ref, _, y) in enumerate(items_sorted):
            new_x = x_min + step * i
            self._apply_node_position(kind, ref, new_x, y)

        self._contour_item._rebuild_nodes()
        self._contour_item._rebuild_extra_nodes()
        self._contour_item._rebuild_path()
        self._mark_modified()
        self.statusBar().showMessage(
            f"Распределено по X ({n} узлов)", 2000,
        )

    def _distribute_y(self) -> None:
        """Равномерно распределить узлы (main + extra) по Y."""
        items = self._get_selected_nodes()
        if len(items) < 3:
            self.statusBar().showMessage(
                "Выдели 3+ узла для распределения", 3000,
            )
            return

        items_sorted = sorted(items, key=lambda t: t[3])
        ys = [y for _, _, _, y in items_sorted]
        y_min, y_max = ys[0], ys[-1]
        n = len(items_sorted)
        step = (y_max - y_min) / (n - 1)

        self._push_contour_snapshot()
        for i, (kind, ref, x, _) in enumerate(items_sorted):
            new_y = y_min + step * i
            self._apply_node_position(kind, ref, x, new_y)

        self._contour_item._rebuild_nodes()
        self._contour_item._rebuild_extra_nodes()
        self._contour_item._rebuild_path()
        self._mark_modified()
        self.statusBar().showMessage(
            f"Распределено по Y ({n} узлов)", 2000,
        )

    def _update_size_display(self) -> None:
        """Показать размер bbox контура в метрах."""
        if not hasattr(self, "_size_label"):
            return
        if self._contour_item is None:
            self._size_label.setText("")
            return

        c = self._contour_item.contour
        all_pts = list(c.points) + list(c.extra_points)
        if not all_pts:
            self._size_label.setText("")
            return

        xs = [p[0] for p in all_pts]
        ys = [p[1] for p in all_pts]
        w = max(xs) - min(xs)
        h = max(ys) - min(ys)
        self._size_label.setText(f"Размер: {w:.2f} × {h:.2f} м")

    def _on_scale_clicked(self) -> None:
        """Масштабировать контур пропорционально."""
        if self._contour_item is None:
            self.statusBar().showMessage(
                "Сначала открой ассет", 3000,
            )
            return

        c = self._contour_item.contour
        all_pts = list(c.points) + list(c.extra_points)
        if not all_pts:
            self.statusBar().showMessage(
                "Контур пустой", 3000,
            )
            return

        xs = [p[0] for p in all_pts]
        ys = [p[1] for p in all_pts]
        w = max(xs) - min(xs)
        h = max(ys) - min(ys)
        if w < 1e-9 and h < 1e-9:
            self.statusBar().showMessage(
                "Контур вырожденный", 3000,
            )
            return

        dlg = ScaleDialog(w, h, self)
        if dlg.exec() != ScaleDialog.DialogCode.Accepted:
            return

        target_w = dlg.result_w
        target_h = dlg.result_h
        if target_w <= 0 or target_h <= 0:
            return

        kx = target_w / w if w > 1e-9 else 1.0
        ky = target_h / h if h > 1e-9 else 1.0

        min_x = min(xs)
        min_y = min(ys)

        self._push_contour_snapshot()

        def scale_pt(p):
            return (
                min_x + (p[0] - min_x) * kx,
                min_y + (p[1] - min_y) * ky,
            )

        c.points = [scale_pt(p) for p in c.points]
        c.extra_points = [scale_pt(p) for p in c.extra_points]

        self._contour_item._rebuild_nodes()
        self._contour_item._rebuild_extra_nodes()
        self._contour_item._rebuild_path()
        self._mark_modified()

        self.statusBar().showMessage(
            f"Масштабировано: {target_w:.2f} × {target_h:.2f} м", 3000,
        )

    def _toggle_extra_actions(self, checked: bool) -> None:
        """Показать / скрыть дополнительные кнопки."""
        actions = getattr(self, "_extra_actions", [])
        tb = getattr(self, "_toolbar", None)
        if tb is None:
            return
        if checked:
            for a in actions:
                tb.addAction(a)
        else:
            for a in actions:
                tb.removeAction(a)

    def _update_node_coords(self) -> None:
        """V16: показать X/Y одного узла или W×H группы."""
        if self._scene is None:
            return
        from .view.items.node_item import NodeItem
        from .view.items.extra_node_item import ExtraNodeItem

        selected = self._scene.selectedItems()
        main_nodes = [it for it in selected if isinstance(it, NodeItem)]
        extra_nodes = [
            it for it in selected if isinstance(it, ExtraNodeItem)
        ]
        total = len(main_nodes) + len(extra_nodes)

        if total == 0:
            self._coord_label.setText("")
            return

        if total == 1:
            n = main_nodes[0] if main_nodes else extra_nodes[0]
            p = n.pos()
            self._coord_label.setText(
                f"X: {p.x():.3f}  Y: {p.y():.3f} м"
            )
            return

        # Несколько — W×H
        xs, ys = [], []
        for n in main_nodes + extra_nodes:
            p = n.pos()
            xs.append(p.x())
            ys.append(p.y())
        w = max(xs) - min(xs)
        h = max(ys) - min(ys)
        self._coord_label.setText(
            f"Узлов: {total}   W×H: {w:.2f} × {h:.2f} м"
        )

    def _on_undo(self) -> None:
        if not self._undo_stack:
            self.statusBar().showMessage("Нечего отменять", 2000)
            return

        self._in_undo_redo = True

        entry = self._undo_stack.pop()
        item = entry[0]
        snapshot = entry[1]

        # A-доп: сохранить текущее состояние в redo (для Ctrl+Shift+Z).
        # Делаем ДО restore, чтобы redo мог вернуться.
        if item is not None:
            try:
                current_snap = item.contour.snapshot()
                self._redo_stack.append((item, current_snap))
            except Exception:
                pass

        # A-доп: запомнить выделенные узлы ДО rebuild
        # (rebuild пересоздаёт NodeItem/ExtraNodeItem — объекты
        # теряются, а с ними и выделение).
        selected_main_idx: set[int] = set()
        selected_extra_ids: set[str] = set()
        for n in getattr(item, "_nodes", []):
            if n.isSelected():
                selected_main_idx.add(n.idx)
        for n in getattr(item, "_extra_nodes", []):
            if n.isSelected():
                selected_extra_ids.add(n.node_id)

        # snapshot — либо dict (новый формат), либо list (старый)
        if isinstance(snapshot, dict):
            tag = "dict"
            item.contour.restore(snapshot)
        else:
            tag = "legacy-list"
            item.contour.points = list(snapshot)

        e2 = entry[2] if len(entry) >= 3 else None
        print(f"[UNDO] entry len={len(entry)}, "
              f"snapshot={tag}, "
              f"entry[2]={e2!r}, "
              f"stack left={len(self._undo_stack)}")

        item._selected_edge_idx = None
        item._selected_extra = None
        item._hover_edge_idx = None
        item._hover_extra = None

        item._rebuild_nodes()
        item._rebuild_extra_nodes()
        item._rebuild_path()

        # A-доп: восстановить выделение по запомненным id.
        # Откладываем через QTimer — чтобы rebuild сцены успел
        # завершиться и объекты точно существовали.
        from PySide6.QtCore import QTimer as _QT

        def _restore_selection():
            if item is None:
                return
            for n in getattr(item, "_nodes", []):
                if n.idx in selected_main_idx:
                    n.setSelected(True)
            for n in getattr(item, "_extra_nodes", []):
                if n.node_id in selected_extra_ids:
                    n.setSelected(True)

        _QT.singleShot(0, _restore_selection)

        # Запись от параметра: (item, snapshot, param_id, old_value)
        if len(entry) >= 4:
            param_id = entry[2]
            old_value = entry[3]
            if self._current_asset is not None:
                p = self._current_asset.get_parameter(param_id)
                if p is not None:
                    p.value = old_value
                    self._parameters_panel.refresh()

        self._reset_param_undo_session()
        self._mark_modified()
        self._check_contour_invariants("после undo")
        self.statusBar().showMessage("Отменено", 2000)
        self._in_undo_redo = False

    def _on_redo(self) -> None:
        """Ctrl+Shift+Z / Ctrl+Y — вернуть отменённое."""
        if not self._redo_stack:
            self.statusBar().showMessage("Нечего возвращать", 2000)
            return

        self._in_undo_redo = True

        entry = self._redo_stack.pop()
        item = entry[0]
        snapshot = entry[1]

        # Записать текущее в undo (без очистки redo)
        if item is not None:
            try:
                current_snap = item.contour.snapshot()
                self._record_undo((item, current_snap))
            except Exception:
                pass

        # Запомнить выделение
        selected_main_idx: set = set()
        selected_extra_ids: set = set()
        for n in getattr(item, "_nodes", []):
            if n.isSelected():
                selected_main_idx.add(n.idx)
        for n in getattr(item, "_extra_nodes", []):
            if n.isSelected():
                selected_extra_ids.add(n.node_id)

        # Restore
        if isinstance(snapshot, dict):
            item.contour.restore(snapshot)
        else:
            item.contour.points = list(snapshot)

        item._selected_edge_idx = None
        item._selected_extra = None
        item._hover_edge_idx = None
        item._hover_extra = None

        item._rebuild_nodes()
        item._rebuild_extra_nodes()
        item._rebuild_path()

        from PySide6.QtCore import QTimer as _QT

        def _restore_selection():
            if item is None:
                return
            for n in getattr(item, "_nodes", []):
                if n.idx in selected_main_idx:
                    n.setSelected(True)
            for n in getattr(item, "_extra_nodes", []):
                if n.node_id in selected_extra_ids:
                    n.setSelected(True)

        _QT.singleShot(0, _restore_selection)

        self._mark_modified()
        self.statusBar().showMessage("Возвращено", 2000)
        self._in_undo_redo = False

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
                    # Сбрасываем и подсветку группы
                    self._contour_item.clear_highlight()
                    self._contour_item.update()

                # Сброс выделения в панелях
                self._groups_panel.clear_selection()
                self._parameters_panel.clear_selection()

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

    def _on_rubber_band_finished(self, rect) -> None:
        """Выделить все узлы (main + extra) внутри прямоугольника."""
        if self._contour_item is None:
            return

        self._scene.clearSelection()

        n = 0
        for item in self._scene.items():
            if not isinstance(item, (NodeItem, ExtraNodeItem)):
                continue
            # У узлов флаг ItemIgnoresTransformations, поэтому
            # sceneBoundingRect неточен. Проверяем центр узла.
            if rect.contains(item.scenePos()):
                item.setSelected(True)
                n += 1

        if n > 0:
            self.statusBar().showMessage(
                f"Выделено узлов: {n}", 2000,
            )
        else:
            self.statusBar().showMessage(
                "Ни один узел не попал в область", 2000,
            )

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
            self._contour_item._update_handle_visibility()
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

        item = self._contour_item

        # ---- EXTRA NODES (ExtraNodeItem) -----------------------
        extra_nodes = [
            it for it in self._scene.selectedItems()
            if isinstance(it, ExtraNodeItem)
        ]
        if extra_nodes:
            snapshot = item.contour.snapshot()

            n = 0
            for node in extra_nodes:
                if item.contour.remove_extra_point(node.node_id):
                    n += 1

            if n > 0:
                item._selected_extra = None
                item._hover_extra = None
                item._rebuild_extra_nodes()
                item.update()

                self._record_undo((item, snapshot))
                self._mark_modified()
                self.statusBar().showMessage(
                    f"Удалено extra-узлов: {n}", 2500,
                )
                return True

        # ---- EXTRA EDGE ----------------------------------------
        extra = getattr(item, "_selected_extra", None)
        if extra is not None:
            a_id, b_id = extra
            snapshot = item.contour.snapshot()

            if item.contour.remove_extra_edge(a_id, b_id):
                # Каскад: подчистить висящие extra-узлы
                item.prune_dangling_extra_nodes()

                item._selected_extra = None
                item._hover_extra = None
                item._rebuild_extra_nodes()
                item.update()

                self._record_undo((item, snapshot))
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
        snapshot = item.contour.snapshot()

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

        self._record_undo((item, snapshot))
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
        self._record_undo((item, snapshot))
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
