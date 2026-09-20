"""
AssetPalette — список Asset'ов для Constructor.
"""
from __future__ import annotations
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel, QListWidget, QListWidgetItem, QPushButton,
    QVBoxLayout, QWidget, QFrame,
)


class AssetPalette(QWidget):
    asset_selected = Signal(str)
    asset_add_requested = Signal(str)
    refresh_requested = Signal()
    WIDTH = 260

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(self.WIDTH)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Ассеты")
        title.setStyleSheet(
            "font-weight: 600; font-size: 12px; color: #1A1A1A;")
        layout.addWidget(title)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        self._list = QListWidget()
        self._list.itemClicked.connect(self._on_clicked)
        self._list.itemDoubleClicked.connect(self._on_double)
        layout.addWidget(self._list, 1)

        hint = QLabel("Двойной клик — добавить на сцену")
        hint.setStyleSheet("color: #888888; font-size: 10px;")
        layout.addWidget(hint)

        btn = QPushButton("Обновить")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self.refresh_requested.emit)
        layout.addWidget(btn)

    def set_assets(self, assets: list) -> None:
        self._list.clear()
        if not assets:
            item = QListWidgetItem("— нет ассетов —")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self._list.addItem(item)
            return
        for a in assets:
            item = QListWidgetItem(f"{a.name}  [{a.type}]")
            item.setData(Qt.ItemDataRole.UserRole, a.id)
            self._list.addItem(item)

    def clear_selection(self) -> None:
        self._list.clearSelection()

    def _on_clicked(self, item) -> None:
        aid = item.data(Qt.ItemDataRole.UserRole)
        if aid:
            self.asset_selected.emit(aid)

    def _on_double(self, item) -> None:
        aid = item.data(Qt.ItemDataRole.UserRole)
        if aid:
            self.asset_add_requested.emit(aid)
