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
from .view.scene import ConstructorScene
from .view.palette import AssetPalette
from .view.properties_panel import PropertiesPanel
from .view.asset_open_dialog import AssetOpenDialog
from .view.items.component_item import ComponentItem
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
        self._build_ui()
        self._connect_signals()
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

        self._act_back = QAction("← Назад", self)
        self._act_back.setShortcut(QKeySequence("Alt+Left"))
        self._act_back.setEnabled(False)
        self._act_back.triggered.connect(self._on_nav_back)
        tb.addAction(self._act_back)

    def _build_ui(self) -> None:
        self._build_toolbar()

        self._properties = PropertiesPanel()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._palette)
        splitter.addWidget(self._canvas)
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
        if not self._current_composite.add_component(comp):
            self.statusBar().showMessage(
                "Компонент не добавлен (дубликат или self-ref)", 3000)
            return

        # Item на сцене
        item = ComponentItem(
            comp, asset=asset, registry=self._registry,
        )
        item.moved.connect(self._on_item_moved)
        item.enter_requested.connect(self._on_enter_composite)
        self._items_by_comp_id[comp.id] = item
        self._scene.addItem(item)

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
            self._items_by_comp_id[comp.id] = item
            self._scene.addItem(item)

        msg = (
            f"Загружено: {asset.name} · "
            f"{len(asset.components)} компонентов"
        )
        if n_orphan:
            msg += f" · {n_orphan} битых"
        self.statusBar().showMessage(msg, 5000)

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

        self._properties.show_component(comp_item.component)

    def _on_prop_value_changed(
        self, comp_id: str, field: str, value: float,
    ) -> None:
        """Панель изменила свойство — применить к item."""
        comp = self._current_composite.get_component(comp_id)
        item = self._items_by_comp_id.get(comp_id)
        if comp is None or item is None:
            return

        if field == "x":
            comp.x = value
        elif field == "y":
            comp.y = value
        elif field == "rotation":
            comp.rotation = value
        elif field == "scale":
            comp.scale = value

        item.apply_from_component()

    def _on_prop_delete(self, comp_id: str) -> None:
        """Удалить компонент."""
        item = self._items_by_comp_id.pop(comp_id, None)
        if item is not None:
            self._scene.removeItem(item)

        self._current_composite.remove_component(comp_id)
        self._properties.clear()
        self.statusBar().showMessage(
            f"Компонент удалён. Всего: "
            f"{self._current_composite.component_count()}", 3000,
        )

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

    def _on_asset_selected(self, asset_id: str) -> None:
        self.statusBar().showMessage(
            f"Выбран: {asset_id} (drag&drop в V8b-2)", 3000)

    def _on_mouse_moved(self, x: float, y: float) -> None:
        self.statusBar().showMessage(f"X={x:.2f} м · Y={y:.2f} м", 0)
