"""
Диалог создания/редактирования одного Condition.

Используется в Inspector при добавлении/редактировании
условия у ChoiceOption.

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

from ..model.condition import (
    Condition,
    VALID_FLAG_OPERATORS,
)


# Операторы, доступные в UI (без reserved: contains, is_null, is_not_null)
UI_VARIABLE_OPERATORS = (
    "==", "!=", ">", "<", ">=", "<=",
)


class ConditionDialog(QDialog):
    """Диалог одного условия."""

    def __init__(self, project_data=None, condition=None, parent=None):
        """
        condition=None — создание нового.
        condition=Condition — редактирование.
        """
        super().__init__(parent)

        self.project_data = project_data
        self.result_condition = None

        self._is_edit = condition is not None
        self._original = condition

        self.setWindowTitle(
            "Редактировать условие" if self._is_edit
            else "Новое условие"
        )
        self.resize(480, 260)

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

        # target — dynamic
        self.target_combo = QComboBox()
        self.target_edit = QLineEdit()
        self.target_edit.setPlaceholderText("имя переменной/флага")

        # Всё — через QLineEdit с автодополнением из project_data
        form.addRow("Имя:", self.target_edit)

        # operator — dynamic
        self.operator_combo = QComboBox()
        form.addRow("Оператор:", self.operator_combo)

        # value — dynamic (QLineEdit или QCheckBox)
        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("значение")

        self.value_bool = QCheckBox("true")
        self.value_bool.setStyleSheet("color: #E5E5E5;")

        # Контейнер для value — используем QLineEdit или QCheckBox
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

        # Инициализация после построения UI
        self._on_kind_changed()

    def _on_kind_changed(self):
        """Переключение kind — обновляем операторы и вид value."""
        kind = self.kind_combo.currentData()

        # Операторы
        self.operator_combo.clear()

        if kind == "variable":
            for op in UI_VARIABLE_OPERATORS:
                self.operator_combo.addItem(op, op)
            self.value_edit.show()
            self.value_bool.hide()
            self.target_edit.setPlaceholderText("имя переменной")
        else:
            for op in VALID_FLAG_OPERATORS:
                self.operator_combo.addItem(op, op)
            self.value_edit.hide()
            self.value_bool.show()
            self.target_edit.setPlaceholderText("имя флага")

    def _load_from(self, condition):
        """Заполняет поля из Condition."""
        # kind
        idx = self.kind_combo.findData(condition.kind)
        if idx >= 0:
            self.kind_combo.blockSignals(True)
            self.kind_combo.setCurrentIndex(idx)
            self.kind_combo.blockSignals(False)

        self._on_kind_changed()

        # target
        self.target_edit.setText(condition.target or "")

        # operator
        idx = self.operator_combo.findData(condition.operator)
        if idx >= 0:
            self.operator_combo.setCurrentIndex(idx)

        # value
        if condition.kind == "flag":
            self.value_bool.setChecked(bool(condition.value))
        else:
            self.value_edit.setText(
                str(condition.value) if condition.value is not None else ""
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