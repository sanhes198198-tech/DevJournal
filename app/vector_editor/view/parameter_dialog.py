"""
ParameterDialog — создание / редактирование параметра Asset'а.

Параметр: имя + value + список таргетов (группа + koef_x + koef_y).

Диалог работает с копией, НЕ мутирует original до accept().
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QMessageBox,
)

from ..model.parameter import Parameter, ParameterTarget


KNOWN_PARAM_TYPES: list[tuple[str, str]] = [
    ("height", "Высота"),
    ("width", "Ширина"),
    ("depth", "Глубина"),
    ("offset", "Смещение"),
    ("scale", "Масштаб"),
    ("angle", "Угол"),
]

CUSTOM_TYPE_SLUG = "__custom__"


class ParameterDialog(QDialog):
    """Диалог параметра."""

    def __init__(self, asset, parameter=None, parent=None):
        super().__init__(parent)

        self._asset = asset
        self._original = parameter
        self._is_edit = parameter is not None

        self.result_parameter: Parameter | None = None

        # Рабочая копия — original не трогаем до accept
        if self._is_edit:
            self._name = parameter.name
            self._label = parameter.label
            self._value = parameter.value
            self._unit = parameter.unit
            self._targets = [
                ParameterTarget(t.group_id, t.koef_x, t.koef_y)
                for t in parameter.targets
            ]
        else:
            self._name = ""
            self._label = ""
            self._value = 0.0
            self._unit = "м"
            self._targets = []

        self.setWindowTitle(
            "Редактировать параметр" if self._is_edit
            else "Новый параметр"
        )
        self.resize(560, 560)

        self._build_ui()
        self._refresh_group_combo()
        self._refresh_targets_list()

        if self._is_edit:
            self._load_from_original()

    # ------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(
            "Редактировать параметр" if self._is_edit
            else "Новый параметр"
        )
        title.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(title)

        # --- Основные поля ---
        form = QFormLayout()
        form.setSpacing(8)

        # Тип — dropdown
        self._type_combo = QComboBox()
        self._type_combo.addItem("— выбери тип —", "")
        for slug, label in KNOWN_PARAM_TYPES:
            self._type_combo.addItem(
                f"{label}  ({slug})", slug,
            )
        self._type_combo.addItem("Свой…", CUSTOM_TYPE_SLUG)
        self._type_combo.currentIndexChanged.connect(
            self._on_type_changed
        )
        form.addRow("Тип:", self._type_combo)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("width, height, wall_offset…")
        form.addRow("Имя (slug):", self._name_edit)

        self._label_edit = QLineEdit()
        self._label_edit.setPlaceholderText("Ширина, Высота…")
        form.addRow("Название:", self._label_edit)

        self._value_spin = QDoubleSpinBox()
        self._value_spin.setRange(-1e6, 1e6)
        self._value_spin.setDecimals(3)
        self._value_spin.setSingleStep(0.1)
        form.addRow("Значение:", self._value_spin)

        self._unit_edit = QLineEdit("м")
        self._unit_edit.setPlaceholderText("м")
        form.addRow("Единица:", self._unit_edit)

        layout.addLayout(form)

        # --- Таргеты ---
        targets_box = QGroupBox("Цели (группы)")
        targets_box.setStyleSheet(
            "QGroupBox { font-size: 11px; color: #E5E5E5; "
            "border: 1px solid #2A2D33; border-radius: 3px; "
            "margin-top: 8px; padding-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; "
            "subcontrol-position: top left; padding: 0 4px; }"
        )
        tb = QVBoxLayout(targets_box)

        self._targets_list = QListWidget()
        self._targets_list.setStyleSheet(
            "QListWidget { background: #181A1E; color: #E5E5E5; "
            "border: 1px solid #2A2D33; border-radius: 3px; "
            "font-size: 11px; }"
            "QListWidget::item { padding: 5px 8px; }"
            "QListWidget::item:selected { background: #2A2D33; }"
        )
        self._targets_list.setMinimumHeight(120)
        tb.addWidget(self._targets_list)

        # --- Форма добавления ---
        add_form = QFormLayout()
        add_form.setSpacing(6)

        self._group_combo = QComboBox()
        add_form.addRow("Группа:", self._group_combo)

        koef_row = QHBoxLayout()
        self._koef_x_spin = QDoubleSpinBox()
        self._koef_x_spin.setRange(-100, 100)
        self._koef_x_spin.setDecimals(3)
        self._koef_x_spin.setSingleStep(0.1)
        self._koef_x_spin.setValue(1.0)
        koef_row.addWidget(QLabel("koef_x:"))
        koef_row.addWidget(self._koef_x_spin, 1)

        self._koef_y_spin = QDoubleSpinBox()
        self._koef_y_spin.setRange(-100, 100)
        self._koef_y_spin.setDecimals(3)
        self._koef_y_spin.setSingleStep(0.1)
        self._koef_y_spin.setValue(0.0)
        koef_row.addWidget(QLabel("koef_y:"))
        koef_row.addWidget(self._koef_y_spin, 1)

        koef_widget = QVBoxLayout()
        koef_widget.addLayout(koef_row)

        add_btn = QPushButton("+ Добавить цель")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._on_add_target)
        self._style_btn(add_btn)

        del_btn = QPushButton("− Удалить цель")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.clicked.connect(self._on_remove_target)
        self._style_btn(del_btn)

        btn_row = QHBoxLayout()
        btn_row.addWidget(add_btn)
        btn_row.addWidget(del_btn)

        tb.addLayout(add_form)
        tb.addLayout(koef_widget)
        tb.addLayout(btn_row)

        layout.addWidget(targets_box, 1)

        # --- Кнопки диалога ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Сохранить")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

    @staticmethod
    def _style_btn(btn: QPushButton) -> None:
        btn.setStyleSheet(
            "QPushButton { background: #202328; color: #E5E5E5; "
            "border: 1px solid #2A2D33; border-radius: 3px; "
            "padding: 5px 8px; font-size: 11px; }"
            "QPushButton:hover { background: #2A2D33; }"
        )

    # ------------------------------------------------------------

    def _on_type_changed(self, idx: int) -> None:
        slug = self._type_combo.currentData()

        if slug == CUSTOM_TYPE_SLUG or slug == "":
            self._apply_custom_mode(True)
            return

        label = ""
        for s, l in KNOWN_PARAM_TYPES:
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

    def _detect_type(self, slug: str) -> str:
        """Определить slug типа по имени параметра."""
        for s, _l in KNOWN_PARAM_TYPES:
            if s == slug:
                return s
        return CUSTOM_TYPE_SLUG

    def _load_from_original(self) -> None:
        # Определить тип по slug
        detected = self._detect_type(self._original.name or "")
        idx = self._type_combo.findData(detected)
        if idx >= 0:
            self._type_combo.blockSignals(True)
            self._type_combo.setCurrentIndex(idx)
            self._type_combo.blockSignals(False)

        if detected == CUSTOM_TYPE_SLUG:
            self._apply_custom_mode(True)
        else:
            self._apply_custom_mode(False)

        self._name_edit.setText(self._original.name)
        self._label_edit.setText(self._original.label)
        self._value_spin.setValue(self._original.value)
        self._unit_edit.setText(self._original.unit)

    def _refresh_group_combo(self) -> None:
        self._group_combo.clear()

        groups = list(self._asset.semantic_groups.values())
        if not groups:
            self._group_combo.addItem("— нет групп —", None)
            self._group_combo.setEnabled(False)
            return

        self._group_combo.setEnabled(True)
        for g in sorted(groups, key=lambda x: (x.label or x.name).lower()):
            self._group_combo.addItem(
                f"{g.label}  ({len(g.node_ids)} узлов)",
                g.id,
            )

    def _refresh_targets_list(self) -> None:
        self._targets_list.clear()
        for t in self._targets:
            group = self._asset.get_semantic_group(t.group_id)
            gname = group.label if group else f"<нет группы {t.group_id}>"
            text = (
                f"{gname}   "
                f"koef_x={t.koef_x:+.2f}  koef_y={t.koef_y:+.2f}"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, t.group_id)
            self._targets_list.addItem(item)

    # ------------------------------------------------------------

    def _on_add_target(self) -> None:
        group_id = self._group_combo.currentData()
        if group_id is None:
            QMessageBox.information(
                self, "Нет групп",
                "В Asset'е нет семантических групп — сначала создайте их.",
            )
            return

        # Заменяем существующий таргет на ту же группу, если есть
        for t in self._targets:
            if t.group_id == group_id:
                t.koef_x = self._koef_x_spin.value()
                t.koef_y = self._koef_y_spin.value()
                self._refresh_targets_list()
                return

        self._targets.append(
            ParameterTarget(
                group_id,
                koef_x=self._koef_x_spin.value(),
                koef_y=self._koef_y_spin.value(),
            )
        )
        self._refresh_targets_list()

    def _on_remove_target(self) -> None:
        item = self._targets_list.currentItem()
        if item is None:
            return
        gid = item.data(Qt.ItemDataRole.UserRole)
        self._targets = [
            t for t in self._targets if t.group_id != gid
        ]
        self._refresh_targets_list()

    # ------------------------------------------------------------

    def _on_accept(self) -> None:
        name = self._name_edit.text().strip()
        label = self._label_edit.text().strip()
        unit = self._unit_edit.text().strip() or "м"
        value = self._value_spin.value()

        if not name:
            self._name_edit.setFocus()
            return
        if not label:
            self._label_edit.setFocus()
            return

        if self._is_edit:
            # Обновляем original ПОСЛЕ валидации
            self._original.name = name
            self._original.label = label
            self._original.unit = unit
            # value НЕ трогаем — им управляет панель через spinbox
            self._original.targets = list(self._targets)
            self.result_parameter = self._original
        else:
            self.result_parameter = Parameter(
                name=name,
                label=label,
                value=value,
                unit=unit,
                targets=list(self._targets),
            )

        self.accept()
