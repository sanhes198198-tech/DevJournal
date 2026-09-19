"""
Диалог создания/редактирования одного Effect.

Используется в Inspector при добавлении/редактировании
эффекта у ChoiceOption.

Не сохраняет изменения сам — возвращает результат в родительский код.
"""

from PySide6.QtWidgets import (
    QDialog,
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

from ..model.effect import (
    Effect,
    VALID_VARIABLE_OPERATIONS,
    VALID_FLAG_OPERATIONS,
)


class EffectDialog(QDialog):
    """Диалог одного эффекта."""

    def __init__(self, project_data=None, effect=None, parent=None):
        """
        effect=None — создание нового.
        effect=Effect — редактирование.
        """
        super().__init__(parent)

        self.project_data = project_data
        self.result_effect = None

        self._is_edit = effect is not None
        self._original = effect

        self.setWindowTitle(
            "Редактировать эффект" if self._is_edit
            else "Новый эффект"
        )
        self.resize(480, 260)

        self._build_ui()

        if effect is not None:
            self._load_from(effect)

    # =========================================================
    # UI
    # =========================================================

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(
            "Редактировать эффект" if self._is_edit
            else "Новый эффект"
        )
        title.setStyleSheet(
            "font-weight: 600; font-size: 13px;"
        )
        layout.addWidget(title)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # --- Форма ---
        form = QFormLayout()
        form.setSpacing(8)
        form.setContentsMargins(0, 0, 0, 0)

        # kind
        self.kind_combo = QComboBox()
        self.kind_combo.addItem("Переменная", "variable")
        self.kind_combo.addItem("Флаг", "flag")
        self.kind_combo.currentIndexChanged.connect(
            self._on_kind_changed
        )
        form.addRow("Тип:", self.kind_combo)

        # target
        self.target_edit = QLineEdit()
        self.target_edit.setPlaceholderText("имя переменной/флага")
        form.addRow("Имя:", self.target_edit)

        # operation
        self.operation_combo = QComboBox()
        form.addRow("Операция:", self.operation_combo)

        # value
        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("значение")

        self.value_bool = QCheckBox("true")
        self.value_bool.setStyleSheet("color: #E5E5E5;")

        value_container = QHBoxLayout()
        value_container.setContentsMargins(0, 0, 0, 0)
        value_container.addWidget(self.value_edit)
        value_container.addWidget(self.value_bool)
        self.value_bool.hide()
        form.addRow("Значение:", value_container)

        layout.addLayout(form)
        layout.addStretch()

        # --- Кнопки ---
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
        """Обновляет список операций и вид value под kind."""
        kind = self.kind_combo.currentData()

        self.operation_combo.clear()

        if kind == "variable":
            for op in VALID_VARIABLE_OPERATIONS:
                self.operation_combo.addItem(op, op)
            self.value_edit.show()
            self.value_bool.hide()
            self.target_edit.setPlaceholderText("имя переменной")
        else:
            for op in VALID_FLAG_OPERATIONS:
                self.operation_combo.addItem(op, op)
            self.value_edit.hide()
            self.value_bool.show()
            self.target_edit.setPlaceholderText("имя флага")

    def _load_from(self, effect):
        """Заполняет поля из Effect."""
        idx = self.kind_combo.findData(effect.kind)
        if idx >= 0:
            self.kind_combo.blockSignals(True)
            self.kind_combo.setCurrentIndex(idx)
            self.kind_combo.blockSignals(False)

        self._on_kind_changed()

        self.target_edit.setText(effect.target or "")

        idx = self.operation_combo.findData(effect.operation)
        if idx >= 0:
            self.operation_combo.setCurrentIndex(idx)

        if effect.kind == "flag":
            self.value_bool.setChecked(bool(effect.value))
        else:
            self.value_edit.setText(
                str(effect.value) if effect.value is not None else ""
            )

    # =========================================================
    # SAVE
    # =========================================================

    def _on_save(self):
        kind = self.kind_combo.currentData()
        target = self.target_edit.text().strip()

        if not target:
            self.target_edit.setFocus()
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
        """Парсит значение из строки: int → float → str."""
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