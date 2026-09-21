"""
SemanticGroupDialog — создание / редактирование одной группы узлов.

Поле node_ids не редактируется вручную — оно берётся из выделения
в сцене (передаётся из панели).

Тип группы выбирается из готового списка. Для нестандартных случаев
есть «Свой…» — тогда поля заполняются вручную.
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

from ..model.semantic_group import SemanticGroup


# Готовые типы групп: (slug, label)
# Порядок — логический: от низа здания к верху, потом горизонталь.
KNOWN_GROUP_TYPES: list[tuple[str, str]] = [
    ("foundation", "Фундамент"),
    ("middle", "Середина"),
    ("facade", "Фасад"),
    ("top", "Корниз"),
    ("left", "Левая грань"),
    ("right", "Правая грань"),
    ("anchor_top", "Якорь верх"),
    ("anchor_bottom", "Якорь низ"),
    ("anchor_left", "Якорь лево"),
    ("anchor_right", "Якорь право"),
]

CUSTOM_SLUG = "__custom__"


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
        self.resize(440, 300)

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

        # Тип — dropdown
        self._type_combo = QComboBox()
        self._type_combo.addItem("— выбери тип —", "")
        for slug, label in KNOWN_GROUP_TYPES:
            self._type_combo.addItem(
                f"{label}  ({slug})", slug,
            )
        self._type_combo.addItem("Свой…", CUSTOM_SLUG)
        self._type_combo.currentIndexChanged.connect(
            self._on_type_changed
        )
        form.addRow("Тип:", self._type_combo)

        # Slug
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(
            "foundation, left_wall, roof_base…"
        )
        form.addRow("Имя (slug):", self._name_edit)

        # Название
        self._label_edit = QLineEdit()
        self._label_edit.setPlaceholderText(
            "Основание, Левая стена…"
        )
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
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            "Сохранить"
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(
            "Отмена"
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

        # По умолчанию — Custom (для нового диалога)
        self._apply_custom_mode(True)

    # ------------------------------------------------------------

    def _on_type_changed(self, idx: int) -> None:
        slug = self._type_combo.currentData()

        if slug == CUSTOM_SLUG or slug == "":
            self._apply_custom_mode(True)
            return

        # Известный тип — заполняем и блокируем
        label = ""
        for s, l in KNOWN_GROUP_TYPES:
            if s == slug:
                label = l
                break

        self._name_edit.setText(slug)
        self._label_edit.setText(label)
        self._apply_custom_mode(False)

    def _apply_custom_mode(self, custom: bool) -> None:
        """True → поля редактируемые, False → только для чтения."""
        self._name_edit.setReadOnly(not custom)
        self._label_edit.setReadOnly(not custom)

        style = (
            "" if custom
            else "background: #F0F0F0; color: #555;"
        )
        self._name_edit.setStyleSheet(style)
        self._label_edit.setStyleSheet(style)

        if custom and self._type_combo.currentData() == "":
            # Пользователь ещё не выбрал — подсказка
            self._name_edit.setFocus()

    # ------------------------------------------------------------

    def _load_from(self, group: SemanticGroup) -> None:
        """Заполнить поля при редактировании существующей группы."""
        slug = group.name or ""
        label = group.label or ""

        # Ищем тип в известных
        known_slug = None
        for s, _l in KNOWN_GROUP_TYPES:
            if s == slug:
                known_slug = s
                break

        self._type_combo.blockSignals(True)

        if known_slug is not None:
            idx = self._type_combo.findData(known_slug)
            if idx >= 0:
                self._type_combo.setCurrentIndex(idx)
            self._apply_custom_mode(False)
        else:
            idx = self._type_combo.findData(CUSTOM_SLUG)
            if idx >= 0:
                self._type_combo.setCurrentIndex(idx)
            self._apply_custom_mode(True)

        self._name_edit.setText(slug)
        self._label_edit.setText(label)

        self._type_combo.blockSignals(False)

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
            self._original.name = name
            self._original.label = label
            self.result_group = self._original
        else:
            self.result_group = SemanticGroup(
                name=name,
                label=label,
                node_ids=list(self._default_node_ids),
            )

        self.accept()