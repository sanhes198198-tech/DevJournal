"""
SaveAssetDialog — диалог сохранения контура как Asset.

Поля:
  - Имя (QLineEdit)
  - Тип (QComboBox, из ASSET_TYPES)

Результат: dlg.name / dlg.asset_type (или None, если отменили).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from ..model.asset import ASSET_TYPES


class SaveAssetDialog(QDialog):
    """Диалог сохранения контура как Asset."""

    def __init__(self, default_name: str = "Новый ассет", parent=None):
        super().__init__(parent)

        self.result_name: str | None = None
        self.result_type: str | None = None

        self.setWindowTitle("Сохранить как Asset")
        self.resize(420, 200)

        self._build_ui(default_name)

    # ------------------------------------------------------------

    def _build_ui(self, default_name: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Сохранить контур как архитектурный ассет")
        title.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(8)

        self._name_edit = QLineEdit()
        self._name_edit.setText(default_name)
        self._name_edit.selectAll()
        form.addRow("Имя:", self._name_edit)

        self._type_combo = QComboBox()
        for type_id, type_label in ASSET_TYPES:
            self._type_combo.addItem(f"{type_label}  ({type_id})", type_id)
        form.addRow("Тип:", self._type_combo)

        layout.addLayout(form)
        layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Сохранить")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

    # ------------------------------------------------------------

    def _on_accept(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            self._name_edit.setFocus()
            return

        self.result_name = name
        self.result_type = self._type_combo.currentData()
        self.accept()
