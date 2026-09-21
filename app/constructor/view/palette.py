"""
AssetPalette — список Asset'ов для Constructor.
Поддерживает multi-select и удаление.
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
    delete_requested = Signal(list)
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
        self._list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        self._list.itemClicked.connect(self._on_clicked)
        self._list.itemDoubleClicked.connect(self._on_double)
        self._list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._list.customContextMenuRequested.connect(
            self._on_context_menu
        )
        layout.addWidget(self._list, 1)

        hint = QLabel(
            "Двойной клик — добавить на сцену\n"
            "Ctrl+клик — выделить несколько"
        )
        hint.setStyleSheet("color: #888888; font-size: 10px;")
        layout.addWidget(hint)

        btn = QPushButton("Обновить")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self.refresh_requested.emit)
        layout.addWidget(btn)

        btn_del = QPushButton("Удалить выбранные")
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet("color: #C0392B;")
        btn_del.clicked.connect(self._on_delete_clicked)
        layout.addWidget(btn_del)

    def set_assets(self, assets: list) -> None:
        self._list.clear()
        if not assets:
            item = QListWidgetItem("— нет ассетов —")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self._list.addItem(item)
            return
        for a in assets:
            is_comp = bool(getattr(a, "components", None))
            icon = "📦 " if is_comp else "  "
            item = QListWidgetItem(f"{icon}{a.name}  [{a.type}]")
            item.setData(Qt.ItemDataRole.UserRole, a.id)
            self._list.addItem(item)

    def clear_selection(self) -> None:
        self._list.clearSelection()

    def _get_selected_ids(self) -> list:
        result = []
        for it in self._list.selectedItems():
            aid = it.data(Qt.ItemDataRole.UserRole)
            if aid:
                result.append(aid)
        return result

    def _on_clicked(self, item) -> None:
        aid = item.data(Qt.ItemDataRole.UserRole)
        if aid:
            self.asset_selected.emit(aid)

    def _on_double(self, item) -> None:
        aid = item.data(Qt.ItemDataRole.UserRole)
        if aid:
            self.asset_add_requested.emit(aid)

    def _on_context_menu(self, pos) -> None:
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        act_del = menu.addAction("Удалить выбранные")
        action = menu.exec(self._list.mapToGlobal(pos))
        if action == act_del:
            self._on_delete_clicked()

    def _on_delete_clicked(self) -> None:
        ids = self._get_selected_ids()
        if not ids:
            return
        self.delete_requested.emit(ids)