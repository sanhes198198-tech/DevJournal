"""
AssetBrowser — левая панель со списком сохранённых Asset'ов.

Двойной клик по элементу → сигнал asset_open_requested(asset_id).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFrame,
)


class AssetBrowser(QWidget):
    """Список Asset'ов из библиотеки."""

    asset_open_requested = Signal(str)
    asset_delete_requested = Signal(str)
    asset_rename_requested = Signal(str)

    WIDTH = 260

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedWidth(self.WIDTH)
        self._build_ui()

    # ------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Assets")
        title.setStyleSheet(
            "font-weight: 600; font-size: 12px; "
            "color: #E5E5E5; padding-bottom: 4px;"
        )
        layout.addWidget(title)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: #2A2D33;")
        layout.addWidget(line)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(
            self._on_item_double_clicked
        )
        self._list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._list.customContextMenuRequested.connect(
            self._on_context_menu
        )
        self._list.setStyleSheet(
            "QListWidget {"
            "  background: #181A1E;"
            "  color: #E5E5E5;"
            "  border: 1px solid #2A2D33;"
            "  border-radius: 3px;"
            "  font-size: 11px;"
            "}"
            "QListWidget::item {"
            "  padding: 6px 8px;"
            "}"
            "QListWidget::item:selected {"
            "  background: #2A2D33;"
            "}"
            "QListWidget::item:hover {"
            "  background: #22262C;"
            "}"
        )
        layout.addWidget(self._list, 1)

        self._hint = QLabel(
            "Двойной клик — открыть"
        )
        self._hint.setStyleSheet(
            "color: #5A5F68; font-size: 10px; padding-top: 4px;"
        )
        layout.addWidget(self._hint)

        self._refresh_button = QPushButton("Обновить")
        self._refresh_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self._refresh_button.setStyleSheet(
            "QPushButton {"
            "  background: #202328;"
            "  color: #E5E5E5;"
            "  border: 1px solid #2A2D33;"
            "  border-radius: 3px;"
            "  padding: 6px 10px;"
            "  font-size: 11px;"
            "}"
            "QPushButton:hover {"
            "  background: #2A2D33;"
            "}"
        )
        self._refresh_button.clicked.connect(self.refresh)
        layout.addWidget(self._refresh_button)

    # ------------------------------------------------------------

    def refresh(self) -> None:
        """Перечитать Assets из библиотеки."""
        from ..io import list_assets

        self._list.clear()

        assets = list_assets()
        if not assets:
            placeholder = QListWidgetItem("— нет assets —")
            placeholder.setFlags(
                placeholder.flags() & ~Qt.ItemFlag.ItemIsSelectable
            )
            self._list.addItem(placeholder)
            return

        for asset in sorted(
            assets,
            key=lambda a: (a.name or a.id).lower(),
        ):
            text = f"{asset.name}  [{asset.type}]"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, asset.id)
            self._list.addItem(item)

    def clear_selection(self) -> None:
        self._list.clearSelection()

    # ------------------------------------------------------------

    def _on_context_menu(self, pos) -> None:
        from PySide6.QtWidgets import QMenu

        item = self._list.itemAt(pos)
        if item is None:
            return
        asset_id = item.data(Qt.ItemDataRole.UserRole)
        if not asset_id:
            return

        menu = QMenu(self)
        act_open = menu.addAction("Открыть")
        act_rename = menu.addAction("Переименовать")
        act_del = menu.addAction("Удалить")

        chosen = menu.exec(self._list.mapToGlobal(pos))
        if chosen is act_open:
            self.asset_open_requested.emit(asset_id)
        elif chosen is act_rename:
            self.asset_rename_requested.emit(asset_id)
        elif chosen is act_del:
            self.asset_delete_requested.emit(asset_id)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        asset_id = item.data(Qt.ItemDataRole.UserRole)
        if asset_id:
            self.asset_open_requested.emit(asset_id)
