"""
SemanticGroupDialog — создание / редактирование одной группы узлов.

Поле node_ids не редактируется вручную — оно берётся из выделения
в сцене (передаётся из панели).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from ..model.semantic_group import SemanticGroup


class SemanticGroupDialog(QDialog):
    """Диалог одной семантической группы."""

    def __init__(
        self,
        group: SemanticGroup | None = None,
        default_node_ids: list[str] | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.result_group: SemanticGroup | None = None

        self._original = group
        self._is_edit = group is not None
        self._default_node_ids = list(default_node_ids or [])

        self.setWindowTitle(
            "Редактировать группу" if self._is_edit
            else "Новая группа"
        )
        self.resize(420, 240)

        self._build_ui()

        if self._is_edit:
            self._load_from(group)

    # ------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(
            "Редактировать группу узлов" if self._is_edit
            else "Новая группа узлов"
        )
        title.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(8)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("foundation, left_wall, roof_base…")
        form.addRow("Имя (slug):", self._name_edit)

        self._label_edit = QLineEdit()
        self._label_edit.setPlaceholderText("Основание, Левая стена…")
        form.addRow("Название:", self._label_edit)

        layout.addLayout(form)

        # Инфо о количестве узлов
        if self._is_edit:
            count = len(self._original.node_ids)
            info_text = f"Узлов в группе: {count}"
        else:
            count = len(self._default_node_ids)
            if count == 0:
                info_text = (
                    "⚠ Ничего не выделено. Выделите узлы (Ctrl+клик) "
                    "в сцене перед созданием группы."
                )
            else:
                info_text = f"Будет добавлено узлов: {count}"

        self._info_label = QLabel(info_text)
        self._info_label.setStyleSheet(
            "color: #858B93; font-size: 11px; padding-top: 4px;"
        )
        self._info_label.setWordWrap(True)
        layout.addWidget(self._info_label)

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

    def _load_from(self, group: SemanticGroup) -> None:
        self._name_edit.setText(group.name)
        self._label_edit.setText(group.label)

    # ------------------------------------------------------------

    def _on_accept(self) -> None:
        name = self._name_edit.text().strip()
        label = self._label_edit.text().strip()

        if not name:
            self._name_edit.setFocus()
            return

        if not label:
            self._label_edit.setFocus()
            return

        if self._is_edit:
            # Обновляем существующую
            self._original.name = name
            self._original.label = label
            # node_ids не трогаем — они привязаны к узлам
            self.result_group = self._original
        else:
            # Создаём новую
            self.result_group = SemanticGroup(
                name=name,
                label=label,
                node_ids=list(self._default_node_ids),
            )

        self.accept()
