"""
AssetOpenDialog — выбор композитного ассета.
Режимы: "open" (открыть) и "delete" (удалить).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class AssetOpenDialog(QDialog):

    def __init__(self, assets: list, mode: str = "open", parent=None):
        super().__init__(parent)
        self._mode = mode

        if mode == "delete":
            self.setWindowTitle("Удалить ассет")
        else:
            self.setWindowTitle("Открыть")
        self.resize(460, 480)

        self._selected_id = None
        self._deleted_id = None
        self._assets = assets

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        if mode == "delete":
            label_text = "Выберите ассет для удаления:"
        else:
            label_text = "Выберите ассет (только составные):"
        layout.addWidget(QLabel(label_text))

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._on_double)
        layout.addWidget(self._list, 1)

        for a in assets:
            comp_count = len(a.components) if a.components else 0
            text = f"{a.name}  [{a.type}]  — {comp_count} комп."
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, a.id)
            self._list.addItem(item)

        if not assets:
            item = QListWidgetItem("— нет составных ассетов —")
            item.setFlags(
                item.flags() & ~Qt.ItemFlag.ItemIsSelectable
            )
            self._list.addItem(item)

        bottom = QHBoxLayout()

        btn_del = QPushButton("Удалить")
        btn_del.clicked.connect(self._on_delete_clicked)
        btn_del.setStyleSheet("color: #C0392B;")
        bottom.addWidget(btn_del)

        bottom.addStretch()

        buttons = QDialogButtonBox()
        if mode == "open":
            ok_btn = buttons.addButton(
                "Открыть", QDialogButtonBox.ButtonRole.AcceptRole,
            )
            ok_btn.clicked.connect(self._on_ok)
        cancel_btn = buttons.addButton(
            "Отмена", QDialogButtonBox.ButtonRole.RejectRole,
        )
        cancel_btn.clicked.connect(self.reject)

        bottom.addWidget(buttons)
        layout.addLayout(bottom)

    def _on_double(self, item) -> None:
        if self._mode == "open":
            self._on_ok()
        else:
            self._on_delete_clicked()

    def _on_ok(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        aid = item.data(Qt.ItemDataRole.UserRole)
        if not aid:
            return
        self._selected_id = aid
        self.accept()

    def _on_delete_clicked(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        aid = item.data(Qt.ItemDataRole.UserRole)
        if not aid:
            return

        name = "?"
        for a in self._assets:
            if a.id == aid:
                name = a.name
                break

        reply = QMessageBox.question(
            self,
            "Удалить ассет",
            "Удалить " + repr(name) + "?\n"
            "Файл будет удалён с диска. Действие необратимо.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._deleted_id = aid
        self.accept()

    def selected_id(self):
        return self._selected_id

    def deleted_id(self):
        return self._deleted_id