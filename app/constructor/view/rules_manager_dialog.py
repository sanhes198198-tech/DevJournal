"""
RulesManagerDialog — управление VisibilityRule композита.

Слева — список правил.
Справа — форма выбранного правила. Изменения автосохраняются.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.vector_editor.model import VisibilityRule


OPERATORS = [(">", ">"), ("<", "<"), (">=", ">="),
             ("<=", "<="), ("==", "=="), ("!=", "!=")]


class RulesManagerDialog(QDialog):
    """Управление правилами показа/скрытия."""

    def __init__(self, composite, registry, parent=None):
        super().__init__(parent)
        self._composite = composite
        self._registry = registry
        self._muted = False
        self._current_rule = None

        self.setWindowTitle("Правила")
        self.resize(820, 560)

        self._build_ui()
        self._refresh_list()

    # ------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Правила показа / скрытия")
        title.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(title)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Левая: список правил ---
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_row_changed)
        lv.addWidget(self._list, 1)

        btns = QHBoxLayout()
        self._btn_new = QPushButton("+ Новое")
        self._btn_new.clicked.connect(self._on_new)
        btns.addWidget(self._btn_new)

        self._btn_del = QPushButton("Удалить")
        self._btn_del.clicked.connect(self._on_delete)
        btns.addWidget(self._btn_del)

        lv.addLayout(btns)

        splitter.addWidget(left)

        # --- Правая: форма ---
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)

        form = QFormLayout()
        form.setSpacing(8)

        self._name_edit = QLineEdit()
        self._name_edit.textChanged.connect(self._on_field_changed)
        form.addRow("Slug:", self._name_edit)

        self._label_edit = QLineEdit()
        self._label_edit.textChanged.connect(self._on_field_changed)
        form.addRow("Название:", self._label_edit)

        self._comp_combo = QComboBox()
        self._comp_combo.currentIndexChanged.connect(
            self._on_comp_changed
        )
        form.addRow("Компонент:", self._comp_combo)

        self._param_combo = QComboBox()
        self._param_combo.currentIndexChanged.connect(
            self._on_field_changed
        )
        form.addRow("Параметр:", self._param_combo)

        self._op_combo = QComboBox()
        for val, txt in OPERATORS:
            self._op_combo.addItem(txt, val)
        self._op_combo.currentIndexChanged.connect(
            self._on_field_changed
        )
        form.addRow("Оператор:", self._op_combo)

        self._value_spin = QDoubleSpinBox()
        self._value_spin.setRange(-1e6, 1e6)
        self._value_spin.setDecimals(3)
        self._value_spin.setSingleStep(0.5)
        self._value_spin.valueChanged.connect(self._on_field_changed)
        form.addRow("Значение:", self._value_spin)

        rv.addLayout(form)

        hint1 = QLabel("Показать когда True:")
        hint1.setStyleSheet("font-size: 11px; padding-top: 6px;")
        rv.addWidget(hint1)

        self._show_list = QListWidget()
        self._show_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        self._show_list.itemSelectionChanged.connect(
            self._on_field_changed
        )
        rv.addWidget(self._show_list, 1)

        hint2 = QLabel("Скрыть когда True:")
        hint2.setStyleSheet("font-size: 11px; padding-top: 6px;")
        rv.addWidget(hint2)

        self._hide_list = QListWidget()
        self._hide_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        self._hide_list.itemSelectionChanged.connect(
            self._on_field_changed
        )
        rv.addWidget(self._hide_list, 1)

        splitter.addWidget(right)
        splitter.setSizes([260, 540])

        layout.addWidget(splitter, 1)

        # Нижние кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        buttons.button(QDialogButtonBox.StandardButton.Close).setText(
            "Закрыть"
        )
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)

    # ------------------------------------------------------------

    def _refresh_list(self) -> None:
        self._muted = True
        self._list.clear()
        self._muted = False

        for r in self._composite.visibility_rules_list():
            item = QListWidgetItem(f"{r.label}  ({r.name})")
            item.setData(Qt.ItemDataRole.UserRole, r.id)
            self._list.addItem(item)

        if self._list.count() > 0:
            self._list.setCurrentRow(0)
        else:
            self._clear_form()

    def _clear_form(self) -> None:
        self._muted = True
        self._name_edit.clear()
        self._label_edit.clear()
        self._comp_combo.clear()
        self._param_combo.clear()
        self._op_combo.setCurrentIndex(0)
        self._value_spin.setValue(0.0)
        self._show_list.clear()
        self._hide_list.clear()
        self._muted = False
        self._current_rule = None

    def _refresh_form_components(self) -> None:
        """Обновить combo компонентов + список show/hide."""
        self._comp_combo.blockSignals(True)
        self._comp_combo.clear()

        for c in self._composite.components.values():
            text = f"{c.name or c.id}  [{c.id[:8]}]"
            self._comp_combo.addItem(text, c.id)

        self._comp_combo.blockSignals(False)

        self._show_list.blockSignals(True)
        self._hide_list.blockSignals(True)
        self._show_list.clear()
        self._hide_list.clear()

        for c in self._composite.components.values():
            text = f"{c.name or c.id}"
            it1 = QListWidgetItem(text)
            it1.setData(Qt.ItemDataRole.UserRole, c.id)
            self._show_list.addItem(it1)

            it2 = QListWidgetItem(text)
            it2.setData(Qt.ItemDataRole.UserRole, c.id)
            self._hide_list.addItem(it2)

        self._show_list.blockSignals(False)
        self._hide_list.blockSignals(False)

    def _refresh_form_params(self) -> None:
        """Обновить combo параметров по выбранному компоненту."""
        self._param_combo.blockSignals(True)
        self._param_combo.clear()

        comp_id = self._comp_combo.currentData()
        if comp_id and self._registry is not None:
            comp = self._composite.components.get(comp_id)
            if comp is not None:
                ref = self._registry.get(comp.asset_id)
                if ref is not None and ref.parameters:
                    for p in ref.parameters_list():
                        self._param_combo.addItem(
                            f"{p.label}  ({p.name})", p.name,
                        )

        self._param_combo.blockSignals(False)

    # ------------------------------------------------------------

    def _on_row_changed(self, row: int) -> None:
        if self._muted or row < 0:
            self._current_rule = None
            return

        item = self._list.item(row)
        if item is None:
            return
        rid = item.data(Qt.ItemDataRole.UserRole)
        rule = self._composite.get_visibility_rule(rid)
        if rule is None:
            return

        self._current_rule = rule
        self._refresh_form_components()
        self._muted = True

        self._name_edit.setText(rule.name)
        self._label_edit.setText(rule.label)

        # Компонент-триггер
        ci = self._comp_combo.findData(rule.component_id)
        if ci >= 0:
            self._comp_combo.setCurrentIndex(ci)

        # Параметры — после выбора компонента
        self._refresh_form_params()
        pi = self._param_combo.findData(rule.parameter_name)
        if pi >= 0:
            self._param_combo.setCurrentIndex(pi)

        # Оператор
        oi = self._op_combo.findData(rule.operator)
        if oi >= 0:
            self._op_combo.setCurrentIndex(oi)

        self._value_spin.setValue(rule.value)

        # show / hide
        for i in range(self._show_list.count()):
            it = self._show_list.item(i)
            cid = it.data(Qt.ItemDataRole.UserRole)
            it.setSelected(cid in rule.show_ids)

        for i in range(self._hide_list.count()):
            it = self._hide_list.item(i)
            cid = it.data(Qt.ItemDataRole.UserRole)
            it.setSelected(cid in rule.hide_ids)

        self._muted = False

    def _on_comp_changed(self, idx: int) -> None:
        if self._muted:
            return
        self._refresh_form_params()
        self._on_field_changed()

    def _on_field_changed(self) -> None:
        if self._muted or self._current_rule is None:
            return

        r = self._current_rule
        r.name = self._name_edit.text().strip() or "rule"
        r.label = self._label_edit.text().strip() or "Правило"

        cid = self._comp_combo.currentData()
        r.component_id = cid or ""

        pid = self._param_combo.currentData()
        r.parameter_name = pid or ""

        r.operator = self._op_combo.currentData() or ">"
        r.value = float(self._value_spin.value())

        r.show_ids = [
            self._show_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._show_list.count())
            if self._show_list.item(i).isSelected()
        ]
        r.hide_ids = [
            self._hide_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._hide_list.count())
            if self._hide_list.item(i).isSelected()
        ]

        # Обновить подпись в списке
        cur = self._list.currentRow()
        if cur >= 0:
            it = self._list.item(cur)
            if it is not None:
                it.setText(f"{r.label}  ({r.name})")

    # ------------------------------------------------------------

    def _on_new(self) -> None:
        r = VisibilityRule(
            name="rule",
            label="Новое правило",
            operator=">",
            value=0.0,
        )
        # Добавим напрямую (is_valid может быть False на старте —
        # добавим в обход проверки)
        self._composite.visibility_rules[r.id] = r
        self._refresh_list()
        # Выбрать последнюю
        for i in range(self._list.count()):
            if self._list.item(i).data(Qt.ItemDataRole.UserRole) == r.id:
                self._list.setCurrentRow(i)
                break

    def _on_delete(self) -> None:
        cur = self._list.currentRow()
        if cur < 0:
            return
        it = self._list.item(cur)
        if it is None:
            return
        rid = it.data(Qt.ItemDataRole.UserRole)
        self._composite.remove_visibility_rule(rid)
        self._refresh_list()
