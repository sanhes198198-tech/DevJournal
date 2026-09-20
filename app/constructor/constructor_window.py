"""
ConstructorWindow — QMainWindow для сборки зданий.
"""
from __future__ import annotations
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel, QMainWindow, QSplitter, QStatusBar, QVBoxLayout, QWidget,
)

from .view.canvas import ConstructorCanvas
from .view.scene import ConstructorScene
from .view.palette import AssetPalette
from .view.properties_panel import PropertiesPanel
from .view.items.component_item import ComponentItem
from app.vector_editor.model import Asset, Component

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
        self._items_by_comp_id: dict = {}
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

    def _build_ui(self) -> None:
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
        item = ComponentItem(comp, asset=asset)
        item.moved.connect(self._on_item_moved)
        self._items_by_comp_id[comp.id] = item
        self._scene.addItem(item)

        self.statusBar().showMessage(
            f"Добавлен: {asset.name} (id={comp.id[:8]}). "
            f"Всего: {self._current_composite.component_count()}",
            4000,
        )

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
