"""
Диалог создания/редактирования одного флага проекта.

Флаг — булево значение:
  - knows_secret: false, "Знает секрет"
  - met_irina: false, "Встречал Ирину"

Не сохраняет изменения сам — возвращает результат в родительский код.
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QLabel,
    QFrame,
)

from ..project_data import Flag
from ..io.storage import _slugify


class FlagDialog(QDialog):
    """Диалог одного флага."""

    def __init__(self, flag=None, existing_ids=None, parent=None):
        """
        flag=None — создание нового.
        flag=Flag — редактирование.
        existing_ids — set() существующих id.
        """
        super().__init__(parent)

        self.result_flag = None

        self._is_edit = flag is not None
        self._original = flag
        self._existing_ids = set(existing_ids or [])

        self.setWindowTitle(
            "Редактировать флаг" if self._is_edit
            else "Новый флаг"
        )
        self.resize(500, 260)

        self._build_ui()

        if flag is not None:
            self._load_from(flag)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(
            "Редактировать флаг" if self._is_edit
            else "Новый флаг"
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
        self.label_edit.setPlaceholderText("Знает секрет")
        self.label_edit.textChanged.connect(self._on_label_changed)
        form.addRow("Название:", self.label_edit)

        # ID
        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("knows_secret")
        if self._is_edit:
            self.id_edit.setReadOnly(True)
            self.id_edit.setToolTip(
                "ID нельзя изменить после создания"
            )
        form.addRow("ID:", self.id_edit)

        # Default
        self.default_check = QCheckBox("Значение по умолчанию: true")
        self.default_check.setStyleSheet("color: #E5E5E5;")
        form.addRow("", self.default_check)

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

    def _on_label_changed(self, text):
        if self._is_edit:
            return
        slug = _slugify(text) if text else ""
        self.id_edit.setText(slug)

    def _load_from(self, flag):
        self.label_edit.setText(flag.label or "")
        self.id_edit.setText(flag.id or "")
        self.default_check.setChecked(bool(flag.default))

    def _on_save(self):
        flag_id = self.id_edit.text().strip()
        label = self.label_edit.text().strip()

        if not flag_id:
            self.id_edit.setFocus()
            return

        if not label:
            self.label_edit.setFocus()
            return

        if not self._is_edit and flag_id in self._existing_ids:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Конфликт",
                f"Флаг с ID «{flag_id}» уже существует.",
            )
            return

        self.result_flag = Flag(
            flag_id=flag_id,
            default=self.default_check.isChecked(),
            label=label,
        )
        self.accept()