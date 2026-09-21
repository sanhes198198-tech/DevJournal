"""
ConstructorWindow — QMainWindow для сборки зданий.
"""
from __future__ import annotations
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel, QMainWindow, QSplitter, QStatusBar, QVBoxLayout, QWidget,
    QToolBar, QMessageBox, QInputDialog,
)
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QGraphicsItem

from .view.canvas import ConstructorCanvas
from .view.ruler import RulerWidget
from .view.scene import ConstructorScene
from .view.palette import AssetPalette
from .view.properties_panel import PropertiesPanel
from .view.asset_open_dialog import AssetOpenDialog
from .view.rules_manager_dialog import RulesManagerDialog
from .view.items.component_item import ComponentItem
from .commands import (
    SetParamOverrideCommand,
    MoveComponentCommand,
    AddComponentCommand,
    DeleteComponentCommand,
    SetPropertyCommand,
)
from PySide6.QtGui import QUndoStack
from app.vector_editor.model import Asset, Component
from app.vector_editor.io import (
    save_asset, load_asset, list_assets, StorageError,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "architecture"))
try:
    from app.architecture.asset_registry import AssetRegistry
except ImportError:
    AssetRegistry = None


class ConstructorWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Constructor — сборка зданий")
        self.resize(1400, 800)

        self._scene = ConstructorScene(self)
        self._canvas = ConstructorCanvas(self._scene, self)
        self._palette = AssetPalette()

        self._registry = None
        self._current_composite = Asset(name="Новый замок", type_="tower_body")
        self._current_asset_id: str | None = None
        self._current_asset_name: str = "Новый замок"
        self._items_by_comp_id: dict = {}
        # Стек навигации: [(asset_id, asset_name), ...]
        # Верх стека — откуда пришли. Пусто = верхний уровень.
        self._nav_stack: list = []
        self._init_registry()
        self._undo_stack = QUndoStack(self)
        self._build_ui()
        self._connect_signals()
        self._setup_undo_shortcuts()
        self._load_assets()

    def _init_registry(self) -> None:
        if AssetRegistry is None:
            return
        try:
            self._registry = AssetRegistry()
            self._registry.load_all()
            print(f"[Constructor] loaded {self._registry.count()} assets")
        except Exception as e:
            print(f"[Constructor] AssetRegistry error: {e}")
            self._registry = None

    def _setup_undo_shortcuts(self) -> None:
        from PySide6.QtGui import QShortcut
        QShortcut(
            QKeySequence("Ctrl+Z"), self,
            lambda: self._undo_stack.undo(),
        )
        QShortcut(
            QKeySequence("Ctrl+Shift+Z"), self,
            lambda: self._undo_stack.redo(),
        )
        QShortcut(
            QKeySequence("Ctrl+Y"), self,
            lambda: self._undo_stack.redo(),
        )

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main", self)
        tb.setMovable(False)
        self.addToolBar(tb)

        act_new = QAction("Новый", self)
        act_new.setShortcut(QKeySequence("Ctrl+N"))
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

        act_open = QAction("Открыть", self)
        act_open.setShortcut(QKeySequence("Ctrl+O"))
        act_open.triggered.connect(self._on_open)
        tb.addAction(act_open)

        tb.addSeparator()

        act_rules = QAction("Правила", self)
        act_rules.setShortcut(QKeySequence("Ctrl+R"))
        act_rules.triggered.connect(self._on_rules_clicked)
        tb.addAction(act_rules)

        tb.addSeparator()

        act_undo = QAction("Отменить", self)
        act_undo.triggered.connect(lambda: self._undo_stack.undo())
        tb.addAction(act_undo)

        act_redo = QAction("Повторить", self)
        act_redo.triggered.connect(lambda: self._undo_stack.redo())
        tb.addAction(act_redo)

        tb.addSeparator()

        self._act_back = QAction("← Назад", self)
        self._act_back.setShortcut(QKeySequence("Alt+Left"))
        self._act_back.setEnabled(False)
        self._act_back.triggered.connect(self._on_nav_back)
        tb.addAction(self._act_back)

    def _build_ui(self) -> None:
        self._build_toolbar()

        self._properties = PropertiesPanel()

        # Canvas + линейки по краям
        from PySide6.QtWidgets import QGridLayout, QWidget as _QW

        self._ruler_h = RulerWidget(self._canvas, "h", self)
        self._ruler_v = RulerWidget(self._canvas, "v", self)

        corner = _QW()
        corner.setFixedSize(22, 22)
        corner.setStyleSheet("background: #F0F2F5;")

        canvas_wrap = _QW()
        gl = QGridLayout(canvas_wrap)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.setSpacing(0)
        gl.addWidget(corner, 0, 0)
        gl.addWidget(self._ruler_h, 0, 1)
        gl.addWidget(self._ruler_v, 1, 0)
        gl.addWidget(self._canvas, 1, 1)
        gl.setRowStretch(1, 1)
        gl.setColumnStretch(1, 1)

        # Синхронизация с зумом/паном
        self._canvas.view_changed.connect(self._ruler_h.update)
        self._canvas.view_changed.connect(self._ruler_v.update)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._palette)
        splitter.addWidget(canvas_wrap)
        splitter.addWidget(self._properties)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setCollapsible(2, False)

        self.setCentralWidget(splitter)
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Constructor V8b-1 готов")

    def _connect_signals(self) -> None:
        self._palette.refresh_requested.connect(self._load_assets)
        self._palette.asset_selected.connect(self._on_asset_selected)
        self._palette.asset_add_requested.connect(self._on_add_asset)
        self._canvas.mouse_moved.connect(self._on_mouse_moved)
        self._scene.selectionChanged.connect(
            self._on_scene_selection_changed
        )
        self._properties.value_changed.connect(
            self._on_prop_value_changed
        )
        self._properties.delete_requested.connect(
            self._on_prop_delete
        )
        self._properties.layer_shift.connect(
            self._on_prop_layer_shift
        )
        self._properties.filled_changed.connect(
            self._on_prop_filled_changed
        )
        self._properties.param_override_changed.connect(
            self._on_prop_param_override
        )

    def _load_assets(self) -> None:
        if self._registry is None:
            self._palette.set_assets([])
            return
        try:
            self._palette.set_assets(self._registry.all())
        except Exception:
            self._palette.set_assets([])

    def _on_add_asset(self, asset_id: str) -> None:
        """Двойной клик в палитре — добавить компонент на сцену."""
        if self._registry is None:
            self.statusBar().showMessage("Реестр ассетов недоступен", 3000)
            return

        asset = self._registry.get(asset_id)
        if asset is None:
            self.statusBar().showMessage(
                f"Ассет {asset_id} не найден", 3000)
            return

        # Создаём компонент в композитном Asset
        comp = Component(
            asset_id=asset_id,
            x=0.0,
            y=0.0,
            rotation=0.0,
            scale=1.0,
            name=asset.name,
        )

        # Через undo-команду
        cmd = AddComponentCommand(
            composite=self._current_composite,
            comp=comp,
            on_create_item=self._create_component_item,
            on_remove_item=self._remove_component_item,
        )
        self._undo_stack.push(cmd)

        self.statusBar().showMessage(
            f"Добавлен: {asset.name} (id={comp.id[:8]}). "
            f"Всего: {self._current_composite.component_count()}",
            4000,
        )

    # ============================================================
    # SAVE / OPEN / NEW
    # ============================================================

    def _reset_scene(self) -> None:
        """Очистить сцену и модель."""
        for item in list(self._scene.items()):
            self._scene.removeItem(item)
        self._items_by_comp_id.clear()
        self._current_composite = Asset(name="Новый замок", type_="tower_body")
        self._current_asset_id = None
        self._current_asset_name = "Новый замок"
        self._nav_stack.clear()
        self._properties.clear()
        self._update_title()

    def _update_title(self) -> None:
        crumbs = [name for (_, name) in self._nav_stack]
        crumbs.append(self._current_asset_name)
        path = " › ".join(crumbs)
        self.setWindowTitle(f"Constructor — {path}")
        if hasattr(self, "_act_back"):
            self._act_back.setEnabled(bool(self._nav_stack))

    def _on_new(self) -> None:
        self._reset_scene()
        self.statusBar().showMessage("Новый замок", 3000)

    def _on_save(self) -> None:
        if self._current_asset_id is None:
            self._on_save_as()
            return

        # Обновляем имя и сохраняем
        self._current_composite.name = self._current_asset_name
        try:
            save_asset(self._current_composite)
        except StorageError as e:
            QMessageBox.critical(
                self, "Ошибка сохранения",
                f"Не удалось сохранить:\n\n{e}",
            )
            return

        self.statusBar().showMessage(
            f"Сохранено: {self._current_asset_name}", 3000,
        )

    def _on_save_as(self) -> None:
        name, ok = QInputDialog.getText(
            self, "Сохранить как",
            "Имя композитного ассета:",
            text=self._current_asset_name,
        )
        if not ok:
            return
        name = name.strip()
        if not name:
            return

        # Новый Asset — с новым uuid, копируем содержимое
        new_asset = Asset(name=name, type_="tower_body")
        new_asset.components = dict(self._current_composite.components)

        try:
            save_asset(new_asset)
        except StorageError as e:
            QMessageBox.critical(
                self, "Ошибка сохранения",
                f"Не удалось сохранить:\n\n{e}",
            )
            return

        self._current_composite = new_asset
        self._current_asset_id = new_asset.id
        self._current_asset_name = name
        self._update_title()

        self.statusBar().showMessage(
            f"Создан: {name} (id={new_asset.id[:8]})", 3000,
        )

    def _on_open(self) -> None:
        # Загружаем все ассеты, фильтруем композитные
        try:
            all_assets = list_assets()
        except Exception as e:
            QMessageBox.warning(
                self, "Ошибка", f"Не удалось загрузить:\n\n{e}")
            return

        composites = [a for a in all_assets if a.components]
        if not composites:
            QMessageBox.information(
                self, "Нет композитных ассетов",
                "Сначала создай и сохрани замок через "
                "«Сохранить как».",
            )
            return

        dlg = AssetOpenDialog(composites, self)
        if dlg.exec() != AssetOpenDialog.DialogCode.Accepted:
            return

        aid = dlg.selected_id()
        if not aid:
            return

        # Загружаем
        target = next(
            (a for a in all_assets if a.id == aid), None
        )
        if target is None:
            return

        # Открытие с верхнего уровня — стек пуст
        self._nav_stack.clear()

        # Перечитать реестр с диска — чтобы подхватить свежие
        # правки из Vector Editor (группы, anchors, контуры)
        if self._registry is not None:
            self._registry.load_all()

        self._load_composite(target)

    def _load_composite(self, asset: Asset) -> None:
        """Загрузить композитный Asset в сцену."""
        self._reset_scene()

        self._current_composite = asset
        self._current_asset_id = asset.id
        self._current_asset_name = asset.name
        self._update_title()

        # N отдельных items — по одному на компонент верхнего уровня.
        # Вложенные composite внутри каждого item отрисуются рекурсивно.
        n_orphan = 0
        for comp in asset.components.values():
            ref_asset = None
            if self._registry is not None:
                ref_asset = self._registry.get(comp.asset_id)
            if ref_asset is None:
                n_orphan += 1

            item = ComponentItem(
                comp, asset=ref_asset, registry=self._registry,
            )
            item.moved.connect(self._on_item_moved)
            item.enter_requested.connect(self._on_enter_composite)
            item.drag_finished.connect(self._on_item_drag_finished)
            item.param_changed.connect(self._on_prop_param_override)
            self._items_by_comp_id[comp.id] = item
            self._scene.addItem(item)

        msg = (
            f"Загружено: {asset.name} · "
            f"{len(asset.components)} компонентов"
        )
        if n_orphan:
            msg += f" · {n_orphan} битых"
        self.statusBar().showMessage(msg, 5000)

        # Применить правила сразу при загрузке
        self._apply_visibility_rules()



    # ============================================================
    # NAVIGATION (вход в composite)
    # ============================================================

    def _on_enter_composite(self, asset_id: str) -> None:
        """Двойной клик по composite — войти внутрь."""
        if self._current_asset_id is None:
            reply = QMessageBox.question(
                self, "Сохранить текущий?",
                "Чтобы войти внутрь, надо сохранить текущий composite.\n\n"
                "Сохранить сейчас?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            self._on_save_as()
            if self._current_asset_id is None:
                return

        # Загружаем sub-asset
        if self._registry is None:
            return
        sub = self._registry.get(asset_id)
        if sub is None:
            QMessageBox.warning(
                self, "Не найдено",
                f"Ассет {asset_id} не найден в библиотеке.",
            )
            return

        # Пушим текущий в стек
        self._nav_stack.append(
            (self._current_asset_id, self._current_asset_name)
        )

        # Загружаем sub как документ
        self._load_composite(sub)

    def _on_nav_back(self) -> None:
        """Вернуться к родителю."""
        if not self._nav_stack:
            return

        parent_id, parent_name = self._nav_stack.pop()

        # Перечитываем parent с диска
        if self._registry is not None:
            self._registry.load_all()
            parent = self._registry.get(parent_id)
        else:
            parent = None

        if parent is None:
            QMessageBox.warning(
                self, "Не найдено",
                f"Родитель {parent_id} не найден.",
            )
            return

        self._load_composite(parent)

    def _on_scene_selection_changed(self) -> None:
        """Обновить панель свойств по выделенному компоненту."""
        items = self._scene.selectedItems()
        comp_item = None
        for it in items:
            if isinstance(it, ComponentItem):
                comp_item = it
                break

        if comp_item is None:
            self._properties.clear()
            return

        # Найти ссылочный ассет компонента (для параметров)
        comp = comp_item.component
        ref_asset = None
        if self._registry is not None:
            ref_asset = self._registry.get(comp.asset_id)

        self._properties.show_component(comp, ref_asset=ref_asset)

    def _apply_property(self, comp_id: str) -> None:
        """После undo/redo свойства — обновить item + панель."""
        comp = self._current_composite.get_component(comp_id)
        item = self._items_by_comp_id.get(comp_id)
        if item is not None:
            item.apply_from_component()

        if (self._properties._current_comp is not None
                and self._properties._current_comp.id == comp_id):
            self._properties.update_values(
                comp.x, comp.y, comp.rotation, comp.scale,
            )
            if hasattr(self._properties, "_layer_spin"):
                self._properties._muted = True
                self._properties._layer_spin.setValue(
                    int(getattr(comp, "layer", 0))
                )
                self._properties._muted = False

    def _on_prop_value_changed(
        self, comp_id: str, field: str, value: float,
    ) -> None:
        """Панель изменила свойство — через undo-команду."""
        comp = self._current_composite.get_component(comp_id)
        item = self._items_by_comp_id.get(comp_id)
        if comp is None or item is None:
            return

        if field not in ("x", "y", "rotation", "scale", "layer"):
            return

        old = getattr(comp, field, None)
        if old is None:
            return

        new = int(value) if field == "layer" else float(value)

        if abs(float(old) - float(new)) < 1e-9:
            return

        cmd = SetPropertyCommand(
            comp, field, old, new,
            on_apply=lambda: self._apply_property(comp_id),
        )
        self._undo_stack.push(cmd)

    def _on_prop_layer_shift(
        self, comp_id: str, direction: int,
    ) -> None:
        """Сдвинуть слой на +1 / -1 — через undo-команду."""
        comp = self._current_composite.get_component(comp_id)
        if comp is None:
            return

        old = int(getattr(comp, "layer", 0))
        new = old + int(direction)

        cmd = SetPropertyCommand(
            comp, "layer", old, new,
            on_apply=lambda: self._apply_property(comp_id),
        )
        self._undo_stack.push(cmd)

    def _on_prop_filled_changed(
        self, comp_id: str, filled: bool,
    ) -> None:
        comp = self._current_composite.get_component(comp_id)
        item = self._items_by_comp_id.get(comp_id)
        if comp is None or item is None:
            return
        comp.filled = bool(filled)
        item.update()

    def _apply_override(self, comp_id: str, name: str) -> None:
        """Применить override к item — пересобрать path + reflow."""
        item = self._items_by_comp_id.get(comp_id)
        if item is not None:
            item.prepareGeometryChange()
            item._rebuild_paths()
            item.update()

        self._reflow_children(comp_id)

        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._apply_visibility_rules)

    def _create_component_item(self, comp) -> "ComponentItem":
        """Создать ComponentItem для компонента, добавить на сцену,
        подключить все сигналы. Возвращает item."""
        ref_asset = None
        if self._registry is not None:
            ref_asset = self._registry.get(comp.asset_id)

        item = ComponentItem(
            comp, asset=ref_asset, registry=self._registry,
        )
        item.moved.connect(self._on_item_moved)
        item.enter_requested.connect(self._on_enter_composite)
        item.drag_finished.connect(self._on_item_drag_finished)
        item.param_changed.connect(self._on_prop_param_override)

        self._items_by_comp_id[comp.id] = item
        self._scene.addItem(item)
        return item

    def _remove_component_item(self, comp_id: str) -> None:
        """Убрать ComponentItem со сцены."""
        item = self._items_by_comp_id.pop(comp_id, None)
        if item is not None:
            self._scene.removeItem(item)

    def _on_prop_param_override(
        self, comp_id: str, name: str, value: float,
    ) -> None:
        """Пользователь меняет параметр sub-ассета — через команду."""
        comp = self._current_composite.get_component(comp_id)
        if comp is None:
            return

        old = comp.param_overrides.get(name)

        # Если значение не изменилось — ничего не делаем
        if old is not None and abs(float(old) - float(value)) < 1e-9:
            return

        cmd = SetParamOverrideCommand(
            comp, name, old, value,
            on_apply=lambda: self._apply_override(comp_id, name),
        )
        self._undo_stack.push(cmd)

    def _on_prop_delete(self, comp_id: str) -> None:
        """Удалить компонент через undo-команду."""
        comp = self._current_composite.get_component(comp_id)
        if comp is None:
            return

        cmd = DeleteComponentCommand(
            composite=self._current_composite,
            comp=comp,
            on_create_item=self._create_component_item,
            on_remove_item=self._remove_component_item,
        )
        self._undo_stack.push(cmd)

        self._properties.clear()
        self.statusBar().showMessage(
            f"Компонент удалён. Всего: "
            f"{self._current_composite.component_count()}", 3000,
        )

    def _on_item_drag_finished(
        self, comp_id: str,
        old_x: float, old_y: float,
        new_x: float, new_y: float,
    ) -> None:
        """Item перетащили — запушить команду в undo stack."""
        comp = self._current_composite.get_component(comp_id)
        if comp is None:
            return

        # Позиция уже применена в mouseRelease — просто фиксируем в истории
        comp.x = old_x
        comp.y = old_y

        item = self._items_by_comp_id.get(comp_id)

        def _apply():
            if item is not None:
                item.setPos(comp.x, comp.y)
                item.update()

        cmd = MoveComponentCommand(
            comp, old_x, old_y, new_x, new_y,
            on_apply=_apply,
        )
        self._undo_stack.push(cmd)

    def _on_item_moved(self) -> None:
        """Item перетащили — обновить значения в панели."""
        items = self._scene.selectedItems()
        for it in items:
            if isinstance(it, ComponentItem):
                c = it.component
                self._properties.update_values(
                    c.x, c.y, c.rotation, c.scale,
                )
                break

    def _reflow_children(
        self, parent_id: str, visited: set | None = None,
    ) -> None:
        """Рекурсивно пересчитать позиции потомков."""
        if self._current_composite is None:
            return
        if visited is None:
            visited = set()
        if parent_id in visited:
            return
        visited.add(parent_id)

        parent_item = self._items_by_comp_id.get(parent_id)
        if parent_item is None:
            return

        from PySide6.QtCore import QPointF

        for child_id, child_item in self._items_by_comp_id.items():
            if child_id in visited:
                continue
            child_comp = self._current_composite.get_component(child_id)
            if child_comp is None:
                continue
            if child_comp.attach_to != parent_id:
                continue
            if not child_comp.attach_anchor or not child_comp.parent_anchor:
                continue

            parent_anchors = parent_item.anchors_local()
            child_anchors = child_item.anchors_local()

            p_local = parent_anchors.get(child_comp.parent_anchor)
            c_local = child_anchors.get(child_comp.attach_anchor)
            if p_local is None or c_local is None:
                continue

            parent_scene = parent_item.mapToScene(
                QPointF(p_local[0], p_local[1])
            )

            new_x = parent_scene.x() - c_local[0]
            new_y = parent_scene.y() - c_local[1]

            child_comp.x = new_x
            child_comp.y = new_y
            child_item.setPos(new_x, new_y)
            child_item.update()

            self._reflow_children(child_id, visited)

    def _apply_visibility_rules(self) -> None:
        """Применить все visibility-правила к items.

        Для каждого правила:
          1. Находим компонент-триггер.
          2. Берём значение параметра (override или родное).
          3. Оцениваем условие.
          4. Для всех компонентов применяем action_for → show/hide.
        """
        if self._current_composite is None:
            return
        rules = self._current_composite.visibility_rules.values()
        if not rules:
            return

        for rule in rules:
            if not rule.enabled:
                continue

            comp = self._current_composite.get_component(
                rule.component_id,
            )
            if comp is None:
                continue

            # Значение параметра
            ov = comp.param_overrides.get(rule.parameter_name)
            if ov is not None:
                value = ov
            else:
                ref = None
                if self._registry is not None:
                    ref = self._registry.get(comp.asset_id)
                if ref is None:
                    continue
                p = None
                for pp in ref.parameters_list():
                    if pp.name == rule.parameter_name:
                        p = pp
                        break
                if p is None:
                    continue
                value = p.value

            condition = rule.evaluate(value)

            # Применяем ко всем загруженным компонентам
            for cid, item in self._items_by_comp_id.items():
                action = rule.action_for(cid, condition)
                if action == "show" and not item.isVisible():
                    item.setVisible(True)
                elif action == "hide" and item.isVisible():
                    item.setVisible(False)

    def _on_rules_clicked(self) -> None:
        """Открыть диалог управления правилами."""
        if self._current_composite is None:
            return
        dlg = RulesManagerDialog(
            self._current_composite, self._registry, self,
        )
        dlg.exec()

    def _on_asset_selected(self, asset_id: str) -> None:
        self.statusBar().showMessage(
            f"Выбран: {asset_id} (drag&drop в V8b-2)", 3000)

    def _on_mouse_moved(self, x: float, y: float) -> None:
        self.statusBar().showMessage(f"X={x:.2f} м · Y={y:.2f} м", 0)
