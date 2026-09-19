"""
Диалог управления переменными и флагами проекта.

Две вкладки:
  - Variables — числовые/строковые значения
  - Flags — булевы значения

Сохраняет project_data.json при закрытии.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
    QFrame,
    QMessageBox,
)

from ..project_data import (
    Variable,
    Flag,
    ProjectData,
)
from ..io import save_project_data
from .variable_dialog import VariableDialog
from .flag_dialog import FlagDialog


class VariablesDialog(QDialog):
    """Диалог управления переменными и флагами проекта."""

    project_data_changed = Signal()

    def __init__(self, project_data, project_folder, parent=None):
        super().__init__(parent)

        self.project_data = project_data
        self.project_folder = project_folder

        # Работаем с копией. Применяем при OK.
        self._working = self._clone_project_data(project_data)

        self.setWindowTitle("Переменные и флаги")
        self.resize(640, 560)

        self._build_ui()
        self._refresh_variables()
        self._refresh_flags()

    # =========================================================
    # DATA
    # =========================================================

    def _clone_project_data(self, pd):
        """Глубокая копия ProjectData."""
        copy = ProjectData()
        for c in pd.characters.values():
            copy.characters[c.id] = c  # characters не трогаем

        for v in pd.variables.values():
            copy.variables[v.id] = Variable.from_dict(v.to_dict())

        for f in pd.flags.values():
            copy.flags[f.id] = Flag.from_dict(f.to_dict())

        return copy

    def _apply_to_original(self):
        """Копирует changes обратно в оригинал."""
        self.project_data.variables = self._working.variables
        self.project_data.flags = self._working.flags

    # =========================================================
    # UI
    # =========================================================

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Переменные и флаги проекта")
        title.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(title)

        hint = QLabel(
            "Переменные — числовые/строковые значения (reputation, gold).\n"
            "Флаги — булевы значения (knows_secret, met_irina).\n"
            "ID используется в условиях и эффектах. Название отображается в UI."
        )
        hint.setStyleSheet("color: #858B93; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # --- Вкладки ---
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        self._build_variables_tab()
        self._build_flags_tab()

        # --- Кнопки внизу ---
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line2)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        bottom.addWidget(btn_cancel)

        bottom.addStretch()

        btn_save = QPushButton("Сохранить")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._on_save_clicked)
        bottom.addWidget(btn_save)

        layout.addLayout(bottom)

    # =========================================================
    # VARIABLES TAB
    # =========================================================

    def _build_variables_tab(self):
        tab = QWidget()
        v = QVBoxLayout(tab)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)

        self.var_list = QListWidget()
        self.var_list.itemDoubleClicked.connect(
            self._on_edit_variable
        )
        v.addWidget(self.var_list, 1)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(6)

        btn_add = QPushButton("+ Добавить")
        btn_add.clicked.connect(self._on_add_variable)
        buttons.addWidget(btn_add)

        btn_edit = QPushButton("Редактировать")
        btn_edit.clicked.connect(self._on_edit_variable)
        buttons.addWidget(btn_edit)

        btn_del = QPushButton("Удалить")
        btn_del.clicked.connect(self._on_delete_variable)
        buttons.addWidget(btn_del)

        buttons.addStretch()
        v.addLayout(buttons)

        self.tabs.addTab(tab, "Переменные")

    def _refresh_variables(self):
        self.var_list.clear()

        vars_list = sorted(
            self._working.variables.values(),
            key=lambda x: (x.label or x.id).lower(),
        )

        for var in vars_list:
            text = (
                f"{var.label}  \u2014  {var.id}  "
                f"[{var.type}]  = {var.default}"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, var.id)
            self.var_list.addItem(item)

        if not vars_list:
            placeholder = QListWidgetItem(
                "— нет переменных. Нажмите «+ Добавить» —"
            )
            placeholder.setFlags(
                placeholder.flags() & ~Qt.ItemFlag.ItemIsSelectable
            )
            placeholder.setForeground(
                self.palette().placeholderText()
            )
            self.var_list.addItem(placeholder)

    def _current_var_id(self):
        item = self.var_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_add_variable(self):
        existing = set(self._working.variables.keys())
        dlg = VariableDialog(
            variable=None,
            existing_ids=existing,
            parent=self,
        )
        dlg.exec()

        if dlg.result_variable is None:
            return

        self._working.add_variable(dlg.result_variable)
        self._refresh_variables()

    def _on_edit_variable(self, *args):
        var_id = self._current_var_id()
        if not var_id:
            return

        var = self._working.get_variable(var_id)
        if var is None:
            return

        dlg = VariableDialog(
            variable=var,
            parent=self,
        )
        dlg.exec()

        if dlg.result_variable is None:
            return

        self._working.variables[var_id] = dlg.result_variable
        self._refresh_variables()

    def _on_delete_variable(self):
        var_id = self._current_var_id()
        if not var_id:
            return

        var = self._working.get_variable(var_id)
        if var is None:
            return

        reply = QMessageBox.question(
            self,
            "Удалить переменную",
            f"Удалить «{var.label}» ({var.id})?\n\n"
            f"Условия и эффекты, ссылающиеся на неё, "
            f"станут невалидными (останутся «висячие» ссылки).",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self._working.remove_variable(var_id)
        self._refresh_variables()

    # =========================================================
    # FLAGS TAB
    # =========================================================

    def _build_flags_tab(self):
        tab = QWidget()
        v = QVBoxLayout(tab)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)

        self.flag_list = QListWidget()
        self.flag_list.itemDoubleClicked.connect(self._on_edit_flag)
        v.addWidget(self.flag_list, 1)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(6)

        btn_add = QPushButton("+ Добавить")
        btn_add.clicked.connect(self._on_add_flag)
        buttons.addWidget(btn_add)

        btn_edit = QPushButton("Редактировать")
        btn_edit.clicked.connect(self._on_edit_flag)
        buttons.addWidget(btn_edit)

        btn_del = QPushButton("Удалить")
        btn_del.clicked.connect(self._on_delete_flag)
        buttons.addWidget(btn_del)

        buttons.addStretch()
        v.addLayout(buttons)

        self.tabs.addTab(tab, "Флаги")

    def _refresh_flags(self):
        self.flag_list.clear()

        flags_list = sorted(
            self._working.flags.values(),
            key=lambda x: (x.label or x.id).lower(),
        )

        for flag in flags_list:
            default_str = "true" if flag.default else "false"
            text = (
                f"{flag.label}  \u2014  {flag.id}  "
                f"= {default_str}"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, flag.id)
            self.flag_list.addItem(item)

        if not flags_list:
            placeholder = QListWidgetItem(
                "— нет флагов. Нажмите «+ Добавить» —"
            )
            placeholder.setFlags(
                placeholder.flags() & ~Qt.ItemFlag.ItemIsSelectable
            )
            placeholder.setForeground(
                self.palette().placeholderText()
            )
            self.flag_list.addItem(placeholder)

    def _current_flag_id(self):
        item = self.flag_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_add_flag(self):
        existing = set(self._working.flags.keys())
        dlg = FlagDialog(
            flag=None,
            existing_ids=existing,
            parent=self,
        )
        dlg.exec()

        if dlg.result_flag is None:
            return

        self._working.add_flag(dlg.result_flag)
        self._refresh_flags()

    def _on_edit_flag(self, *args):
        flag_id = self._current_flag_id()
        if not flag_id:
            return

        flag = self._working.get_flag(flag_id)
        if flag is None:
            return

        dlg = FlagDialog(
            flag=flag,
            parent=self,
        )
        dlg.exec()

        if dlg.result_flag is None:
            return

        self._working.flags[flag_id] = dlg.result_flag
        self._refresh_flags()

    def _on_delete_flag(self):
        flag_id = self._current_flag_id()
        if not flag_id:
            return

        flag = self._working.get_flag(flag_id)
        if flag is None:
            return

        reply = QMessageBox.question(
            self,
            "Удалить флаг",
            f"Удалить «{flag.label}» ({flag.id})?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self._working.remove_flag(flag_id)
        self._refresh_flags()

    # =========================================================
    # SAVE
    # =========================================================

    def _on_save_clicked(self):
        self._apply_to_original()

        try:
            save_project_data(self.project_data, self.project_folder)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Ошибка сохранения",
                f"Не удалось сохранить: {e!r}",
            )
            return

        self.project_data_changed.emit()
        self.accept()