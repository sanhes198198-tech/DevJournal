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
        right_stub = QWidget()
        right_stub.setFixedWidth(220)
        rl = QVBoxLayout(right_stub)
        rl.addWidget(QLabel("Свойства"))
        rl.addStretch()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._palette)
        splitter.addWidget(self._canvas)
        splitter.addWidget(right_stub)
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
        self._scene.addItem(item)

        self.statusBar().showMessage(
            f"Добавлен: {asset.name} (id={comp.id[:8]}). "
            f"Всего: {self._current_composite.component_count()}",
            4000,
        )

    def _on_asset_selected(self, asset_id: str) -> None:
        self.statusBar().showMessage(
            f"Выбран: {asset_id} (drag&drop в V8b-2)", 3000)

    def _on_mouse_moved(self, x: float, y: float) -> None:
        self.statusBar().showMessage(f"X={x:.2f} м · Y={y:.2f} м", 0)
