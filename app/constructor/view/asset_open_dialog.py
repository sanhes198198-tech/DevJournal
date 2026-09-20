"""
AssetOpenDialog — выбор композитного ассета для открытия.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)


class AssetOpenDialog(QDialog):
    """Диалог выбора ассета."""

    def __init__(self, assets: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Открыть")
        self.resize(440, 460)

        self._selected_id: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        label = QLabel("Выберите ассет (только составные):")
        layout.addWidget(label)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._on_double)
        layout.addWidget(self._list, 1)

        for a in assets:
            comp_count = len(a.components) if a.components else 0
            text = f"{a.name}  [{a.type}]  · {comp_count} комп."
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, a.id)
            self._list.addItem(item)

        if not assets:
            item = QListWidgetItem("— нет составных ассетов —")
            item.setFlags(
                item.flags() & ~Qt.ItemFlag.ItemIsSelectable
            )
            self._list.addItem(item)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Открыть")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_double(self, item) -> None:
        self._on_ok()

    def _on_ok(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        aid = item.data(Qt.ItemDataRole.UserRole)
        if not aid:
            return
        self._selected_id = aid
        self.accept()

    def selected_id(self) -> str | None:
        return self._selected_id
