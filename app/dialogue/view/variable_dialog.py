"""
Диалог создания/редактирования одной переменной проекта.

Переменная — числовое или строковое значение игры:
  - reputation: int, "Репутация"
  - gold: int, "Золото"
  - chapter: int, "Глава"

Не сохраняет изменения сам — возвращает результат в родительский код.
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QComboBox,
    QLineEdit,
    QPushButton,
    QLabel,
    QFrame,
)

from ..project_data import (
    Variable,
    VALID_VARIABLE_TYPES,
)
from ..io.storage import _slugify


class VariableDialog(QDialog):
    """Диалог одной переменной."""

    def __init__(self, variable=None, existing_ids=None, parent=None):
        """
        variable=None — создание новой.
        variable=Variable — редактирование.
        existing_ids — set() существующих id (для проверки коллизий).
        """
        super().__init__(parent)

        self.result_variable = None

        self._is_edit = variable is not None
        self._original = variable
        self._existing_ids = set(existing_ids or [])

        self.setWindowTitle(
            "Редактировать переменную" if self._is_edit
            else "Новая переменная"
        )
        self.resize(500, 320)

        self._build_ui()

        if variable is not None:
            self._load_from(variable)

    # =========================================================
    # UI
    # =========================================================

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(
            "Редактировать переменную" if self._is_edit
            else "Новая переменная"
        )
        title.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(title)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        form = QFormLayout()
        form.setSpacing(8)
        form.setContentsMargins(0, 0, 0, 0)

        # Label
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("Репутация")
        self.label_edit.textChanged.connect(self._on_label_changed)
        form.addRow("Название:", self.label_edit)

        # ID
        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("reputation")
        if self._is_edit:
            self.id_edit.setReadOnly(True)
            self.id_edit.setToolTip(
                "ID нельзя изменить после создания"
            )
        form.addRow("ID:", self.id_edit)

        # Type
        self.type_combo = QComboBox()
        type_labels = {
            "int": "Целое число (int)",
            "float": "Дробное число (float)",
            "bool": "Логическое (bool)",
            "string": "Строка (string)",
        }
        for t in VALID_VARIABLE_TYPES:
            self.type_combo.addItem(type_labels.get(t, t), t)
        self.type_combo.currentIndexChanged.connect(
            self._on_type_changed
        )
        form.addRow("Тип:", self.type_combo)

        # Default
        self.default_edit = QLineEdit()
        self.default_edit.setPlaceholderText("0")
        self.default_edit.textChanged.connect(
            self._on_default_changed
        )
        self.default_hint = QLabel("")
        self.default_hint.setStyleSheet(
            "color: #5A5F68; font-size: 10px;"
        )

        default_row = QVBoxLayout()
        default_row.setContentsMargins(0, 0, 0, 0)
        default_row.setSpacing(2)
        default_row.addWidget(self.default_edit)
        default_row.addWidget(self.default_hint)
        form.addRow("Значение по умолчанию:", default_row)

        layout.addLayout(form)
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

        self._on_type_changed()

    # =========================================================
    # SYNC
    # =========================================================

    def _on_label_changed(self, text):
        """Авто-генерация ID из label (только при создании)."""
        if self._is_edit:
            return

        slug = _slugify(text) if text else ""
        self.id_edit.setText(slug)

    def _on_type_changed(self):
        """Подсказка под default + при необходимости значение."""
        t = self.type_combo.currentData()

        hints = {
            "int": "Целое число: 0, 5, -10",
            "float": "Дробное число: 0.0, 3.14, -2.5",
            "bool": "true или false",
            "string": "Любой текст в кавычках не нужен",
        }
        self.default_hint.setText(hints.get(t, ""))

        # Для bool подставляем placeholder
        if t == "bool":
            self.default_edit.setPlaceholderText("false")
        elif t == "float":
            self.default_edit.setPlaceholderText("0.0")
        elif t == "int":
            self.default_edit.setPlaceholderText("0")
        else:
            self.default_edit.setPlaceholderText("")

    def _on_default_changed(self, text):
        """Live-проверка значения."""
        t = self.type_combo.currentData()
        if not text:
            self.default_hint.setStyleSheet(
                "color: #5A5F68; font-size: 10px;"
            )
            return

        ok = self._is_valid_value(text, t)
        if ok:
            self.default_hint.setStyleSheet(
                "color: #7ED321; font-size: 10px;"
            )
        else:
            self.default_hint.setStyleSheet(
                "color: #D0021B; font-size: 10px;"
            )

    # =========================================================
    # LOAD
    # =========================================================

    def _load_from(self, variable):
        self.label_edit.setText(variable.label or "")
        self.id_edit.setText(variable.id or "")

        idx = self.type_combo.findData(variable.type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)

        if variable.default is not None:
            self.default_edit.setText(str(variable.default))

    # =========================================================
    # SAVE
    # =========================================================

    def _on_save(self):
        variable_id = self.id_edit.text().strip()
        label = self.label_edit.text().strip()
        vtype = self.type_combo.currentData()
        default_str = self.default_edit.text().strip()

        if not variable_id:
            self.id_edit.setFocus()
            return

        if not label:
            self.label_edit.setFocus()
            return

        # Коллизия id (только при создании)
        if not self._is_edit and variable_id in self._existing_ids:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Конфликт",
                f"Переменная с ID «{variable_id}» уже существует.",
            )
            return

        # Валидация default
        if default_str and not self._is_valid_value(
            default_str, vtype
        ):
            self.default_edit.setFocus()
            return

        default = self._parse_value(default_str, vtype)

        self.result_variable = Variable(
            variable_id=variable_id,
            var_type=vtype,
            default=default,
            label=label,
        )
        self.accept()

    # =========================================================
    # VALUE HELPERS
    # =========================================================

    @staticmethod
    def _is_valid_value(text, vtype):
        if vtype == "int":
            try:
                int(text)
                return True
            except ValueError:
                return False

        if vtype == "float":
            try:
                float(text)
                return True
            except ValueError:
                return False

        if vtype == "bool":
            return text.lower() in ("true", "false", "1", "0")

        if vtype == "string":
            return True

        return False

    @staticmethod
    def _parse_value(text, vtype):
        if text == "":
            if vtype == "int":
                return 0
            if vtype == "float":
                return 0.0
            if vtype == "bool":
                return False
            return ""

        if vtype == "int":
            try:
                return int(text)
            except ValueError:
                return 0

        if vtype == "float":
            try:
                return float(text)
            except ValueError:
                return 0.0

        if vtype == "bool":
            return text.lower() in ("true", "1")

        return text