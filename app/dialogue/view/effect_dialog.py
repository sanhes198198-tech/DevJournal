"""
Диалог создания/редактирования одного Effect.

Использует project_data для dropdown переменных/флагов.
Показывает русские подписи операций.
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

from ..model.effect import Effect


# Операции, доступные в UI (русские подписи)
UI_VARIABLE_OPERATIONS = (
    ("set",      "установить в"),
    ("add",      "прибавить"),
    ("subtract", "отнять"),
    ("multiply", "умножить на"),
)

UI_FLAG_OPERATIONS = (
    ("set",    "установить в"),
    ("toggle", "переключить"),
)


class EffectDialog(QDialog):
    """Диалог одного эффекта."""

    def __init__(self, project_data=None, effect=None, parent=None):
        super().__init__(parent)

        self.project_data = project_data
        self.result_effect = None

        self._is_edit = effect is not None
        self._original = effect

        self.setWindowTitle(
            "Редактировать эффект" if self._is_edit
            else "Новый эффект"
        )
        self.resize(520, 320)

        self._build_ui()

        if effect is not None:
            self._load_from(effect)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(
            "Редактировать эффект" if self._is_edit
            else "Новый эффект"
        )
        title.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(title)

        hint = QLabel(
            "Что произойдёт, если игрок выберет этот вариант."
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

        # Имя
        self.target_combo = QComboBox()
        self.target_edit = QLineEdit()
        self.target_edit.setPlaceholderText("имя переменной/флага")

        self.target_stack = QWidget()
        ts = QVBoxLayout(self.target_stack)
        ts.setContentsMargins(0, 0, 0, 0)
        ts.setSpacing(0)
        ts.addWidget(self.target_combo)
        ts.addWidget(self.target_edit)
        self.target_edit.hide()
        form.addRow("Имя:", self.target_stack)

        # Операция
        self.operation_combo = QComboBox()
        form.addRow("Операция:", self.operation_combo)

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

    def _on_kind_changed(self):
        kind = self.kind_combo.currentData()

        # Операции
        self.operation_combo.clear()
        ops = UI_VARIABLE_OPERATIONS if kind == "variable" \
            else UI_FLAG_OPERATIONS

        for op_value, op_label in ops:
            self.operation_combo.addItem(op_label, op_value)

        # Target — из project_data
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
        if self.target_combo.isVisible():
            return self.target_combo.currentData() or ""
        return self.target_edit.text().strip()

    def _set_target(self, value):
        if value is None:
            value = ""

        idx = self.target_combo.findData(value)
        if idx >= 0:
            self.target_combo.show()
            self.target_edit.hide()
            self.target_combo.setCurrentIndex(idx)
        else:
            if value:
                self.target_combo.hide()
                self.target_edit.show()
                self.target_edit.setText(value)

    def _on_value_changed(self, text):
        self._update_hint()

    def _update_hint(self):
        kind = self.kind_combo.currentData()
        op = self.operation_combo.currentData() if hasattr(self, "operation_combo") else None

        if kind == "flag":
            if op == "toggle":
                self.value_hint.setText(
                    "Переключение — значение не нужно"
                )
            else:
                self.value_hint.setText(
                    "Установить флаг в true или false"
                )
            self.value_hint.setStyleSheet(
                "color: #5A5F68; font-size: 10px; padding-left: 4px;"
            )
            return

        text = self.value_edit.text().strip()

        if not text:
            self.value_hint.setText(
                "Введите число (5, -10) или строку"
            )
            self.value_hint.setStyleSheet(
                "color: #5A5F68; font-size: 10px; padding-left: 4px;"
            )
            return

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

        self.value_hint.setText(f"Строка: «{text}»")
        self.value_hint.setStyleSheet(
            "color: #858B93; font-size: 10px; padding-left: 4px;"
        )

    def _load_from(self, effect):
        idx = self.kind_combo.findData(effect.kind)
        if idx >= 0:
            self.kind_combo.blockSignals(True)
            self.kind_combo.setCurrentIndex(idx)
            self.kind_combo.blockSignals(False)

        self._on_kind_changed()

        self._set_target(effect.target or "")

        idx = self.operation_combo.findData(effect.operation)
        if idx >= 0:
            self.operation_combo.setCurrentIndex(idx)

        if effect.kind == "flag":
            self.value_bool.setChecked(bool(effect.value))
        else:
            self.value_edit.setText(
                str(effect.value) if effect.value is not None else ""
            )

        self._update_hint()

    def _on_save(self):
        kind = self.kind_combo.currentData()
        target = self._current_target()

        if not target:
            self.value_hint.setText("⚠ Укажите имя переменной/флага")
            self.value_hint.setStyleSheet(
                "color: #D0021B; font-size: 10px; padding-left: 4px;"
            )
            return

        operation = self.operation_combo.currentData() or "set"

        if kind == "flag":
            value = self.value_bool.isChecked()
            self.result_effect = Effect(
                kind="flag",
                flag=target,
                operation=operation,
                value=value,
            )
        else:
            value_str = self.value_edit.text().strip()
            value = self._parse_value(value_str)
            self.result_effect = Effect(
                kind="variable",
                variable=target,
                operation=operation,
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