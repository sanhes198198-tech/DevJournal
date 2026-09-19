"""
Диалог создания/редактирования одного Condition.

Использует project_data для dropdown переменных/флагов.
Показывает русские подписи операторов.
"""

from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QComboBox,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QLabel,
    QFrame,
)

from ..model.condition import (
    Condition,
    VALID_FLAG_OPERATORS,
)


# Операторы, доступные в UI (русские подписи)
UI_VARIABLE_OPERATORS = (
    ("==", "равно"),
    ("!=", "не равно"),
    (">",  "больше"),
    ("<",  "меньше"),
    (">=", "больше или равно"),
    ("<=", "меньше или равно"),
)

UI_FLAG_OPERATORS = (
    ("==", "равно"),
    ("!=", "не равно"),
)


class ConditionDialog(QDialog):
    """Диалог одного условия."""

    def __init__(self, project_data=None, condition=None, parent=None):
        super().__init__(parent)

        self.project_data = project_data
        self.result_condition = None

        self._is_edit = condition is not None
        self._original = condition

        self.setWindowTitle(
            "Редактировать условие" if self._is_edit
            else "Новое условие"
        )
        self.resize(520, 320)

        self._build_ui()

        if condition is not None:
            self._load_from(condition)

    # =========================================================
    # UI
    # =========================================================

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(
            "Редактировать условие" if self._is_edit
            else "Новое условие"
        )
        title.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(title)

        hint = QLabel(
            "Показать вариант выбора только если условие верно."
        )
        hint.setStyleSheet("color: #858B93; font-size: 11px;")
        layout.addWidget(hint)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        form = QFormLayout()
        form.setSpacing(8)
        form.setContentsMargins(0, 0, 0, 0)

        # Тип
        self.kind_combo = QComboBox()
        self.kind_combo.addItem("Переменная (число)", "variable")
        self.kind_combo.addItem("Флаг (true/false)", "flag")
        self.kind_combo.currentIndexChanged.connect(
            self._on_kind_changed
        )
        form.addRow("Тип:", self.kind_combo)

        # Имя — dropdown (или QLineEdit как fallback)
        self.target_combo = QComboBox()
        self.target_edit = QLineEdit()
        self.target_edit.setPlaceholderText("имя переменной/флага")

        self.target_stack = QWidget()
        ts_layout = QVBoxLayout(self.target_stack)
        ts_layout.setContentsMargins(0, 0, 0, 0)
        ts_layout.setSpacing(0)
        ts_layout.addWidget(self.target_combo)
        ts_layout.addWidget(self.target_edit)
        self.target_edit.hide()
        form.addRow("Имя:", self.target_stack)

        # Оператор
        self.operator_combo = QComboBox()
        form.addRow("Оператор:", self.operator_combo)

        # Значение
        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("значение")
        self.value_edit.textChanged.connect(self._on_value_changed)

        self.value_bool = QCheckBox("истина (true)")
        self.value_bool.setStyleSheet("color: #E5E5E5;")

        value_container = QHBoxLayout()
        value_container.setContentsMargins(0, 0, 0, 0)
        value_container.addWidget(self.value_edit)
        value_container.addWidget(self.value_bool)
        self.value_bool.hide()
        form.addRow("Значение:", value_container)

        layout.addLayout(form)

        # Hint валидации
        self.value_hint = QLabel("")
        self.value_hint.setStyleSheet(
            "color: #858B93; font-size: 10px; padding-left: 4px;"
        )
        layout.addWidget(self.value_hint)

        layout.addStretch()

        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line2)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(btn_cancel)

        buttons.addStretch()

        btn_save = QPushButton("Сохранить")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._on_save)
        buttons.addWidget(btn_save)

        layout.addLayout(buttons)

        self._on_kind_changed()

    # =========================================================
    # DYNAMIC
    # =========================================================

    def _on_kind_changed(self):
        kind = self.kind_combo.currentData()

        # Операторы
        self.operator_combo.clear()
        ops = UI_VARIABLE_OPERATORS if kind == "variable" \
            else UI_FLAG_OPERATORS

        for op_value, op_label in ops:
            self.operator_combo.addItem(op_label, op_value)

        # Список target — из project_data
        self._rebuild_target_list(kind)

        # Value вид
        if kind == "flag":
            self.value_edit.hide()
            self.value_bool.show()
        else:
            self.value_edit.show()
            self.value_bool.hide()

        self._update_hint()

    def _rebuild_target_list(self, kind):
        """Перестраивает dropdown переменных/флагов."""
        self.target_combo.clear()

        items = []
        if self.project_data is not None:
            if kind == "variable":
                for v in sorted(
                    self.project_data.variables.values(),
                    key=lambda x: (x.label or x.id).lower(),
                ):
                    items.append((v.id, f"{v.label} ({v.id})"))
            else:
                for f in sorted(
                    self.project_data.flags.values(),
                    key=lambda x: (x.label or x.id).lower(),
                ):
                    items.append((f.id, f"{f.label} ({f.id})"))

        if items:
            self.target_combo.show()
            self.target_edit.hide()
            for value, label in items:
                self.target_combo.addItem(label, value)
        else:
            # Справочник пуст — fallback QLineEdit
            self.target_combo.hide()
            self.target_edit.show()
            if kind == "variable":
                self.target_edit.setPlaceholderText(
                    "Нет переменных — создайте через «Переменные…»"
                )
            else:
                self.target_edit.setPlaceholderText(
                    "Нет флагов — создайте через «Переменные…»"
                )

    def _current_target(self):
        """Возвращает target: из combo или из edit."""
        if self.target_combo.isVisible():
            return self.target_combo.currentData() or ""
        return self.target_edit.text().strip()

    def _set_target(self, value):
        """Устанавливает target (ищет в combo, иначе в edit)."""
        if value is None:
            value = ""

        idx = self.target_combo.findData(value)
        if idx >= 0:
            self.target_combo.show()
            self.target_edit.hide()
            self.target_combo.setCurrentIndex(idx)
        else:
            # Не найден в справочнике — показываем в edit
            if value:
                self.target_combo.hide()
                self.target_edit.show()
                self.target_edit.setText(value)

    # =========================================================
    # VALIDATION HINT
    # =========================================================

    def _on_value_changed(self, text):
        self._update_hint()

    def _update_hint(self):
        kind = self.kind_combo.currentData()

        if kind == "flag":
            self.value_hint.setText(
                "Значение флага — true или false"
            )
            self.value_hint.setStyleSheet(
                "color: #5A5F68; font-size: 10px; padding-left: 4px;"
            )
            return

        text = self.value_edit.text().strip()

        if not text:
            self.value_hint.setText(
                "Введите число (0, 5, -10) или строку"
            )
            self.value_hint.setStyleSheet(
                "color: #5A5F68; font-size: 10px; padding-left: 4px;"
            )
            return

        # Пробуем как число
        try:
            int(text)
            self.value_hint.setText(f"Число: {text}")
            self.value_hint.setStyleSheet(
                "color: #7ED321; font-size: 10px; padding-left: 4px;"
            )
            return
        except ValueError:
            pass

        try:
            float(text)
            self.value_hint.setText(f"Дробное число: {text}")
            self.value_hint.setStyleSheet(
                "color: #7ED321; font-size: 10px; padding-left: 4px;"
            )
            return
        except ValueError:
            pass

        # Иначе — строка (тоже валидно для string переменных)
        self.value_hint.setText(f"Строка: «{text}»")
        self.value_hint.setStyleSheet(
            "color: #858B93; font-size: 10px; padding-left: 4px;"
        )

    # =========================================================
    # LOAD
    # =========================================================

    def _load_from(self, condition):
        idx = self.kind_combo.findData(condition.kind)
        if idx >= 0:
            self.kind_combo.blockSignals(True)
            self.kind_combo.setCurrentIndex(idx)
            self.kind_combo.blockSignals(False)

        self._on_kind_changed()

        self._set_target(condition.target or "")

        idx = self.operator_combo.findData(condition.operator)
        if idx >= 0:
            self.operator_combo.setCurrentIndex(idx)

        if condition.kind == "flag":
            self.value_bool.setChecked(bool(condition.value))
        else:
            self.value_edit.setText(
                str(condition.value) if condition.value is not None else ""
            )

        self._update_hint()

    # =========================================================
    # SAVE
    # =========================================================

    def _on_save(self):
        kind = self.kind_combo.currentData()
        target = self._current_target()

        if not target:
            self.value_hint.setText("⚠ Укажите имя переменной/флага")
            self.value_hint.setStyleSheet(
                "color: #D0021B; font-size: 10px; padding-left: 4px;"
            )
            return

        operator = self.operator_combo.currentData() or "=="

        if kind == "flag":
            value = self.value_bool.isChecked()
            self.result_condition = Condition(
                kind="flag",
                flag=target,
                operator=operator,
                value=value,
            )
        else:
            value_str = self.value_edit.text().strip()
            value = self._parse_value(value_str)
            self.result_condition = Condition(
                kind="variable",
                variable=target,
                operator=operator,
                value=value,
            )

        self.accept()

    @staticmethod
    def _parse_value(text):
        if text == "":
            return None

        try:
            return int(text)
        except ValueError:
            pass

        try:
            return float(text)
        except ValueError:
            pass

        return text