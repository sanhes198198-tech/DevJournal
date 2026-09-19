"""
Диалог управления справочником персонажей проекта.

Add / Edit / Delete персонажей.
Сохраняет project_data.json при закрытии.
"""

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
    QFrame,
    QInputDialog,
    QMessageBox,
)

from ..project_data import Character, ProjectData
from ..io import save_project_data


class CharactersDialog(QDialog):
    """Диалог управления персонажами проекта."""

    # Сигнал: ProjectData изменился (после сохранения)
    project_data_changed = Signal()

    def __init__(self, project_data, project_folder, parent=None):
        super().__init__(parent)

        self.project_data = project_data
        self.project_folder = project_folder

        # Работаем с копией. Применяем при OK.
        self._working = self._clone_project_data(project_data)

        self.setWindowTitle("Персонажи проекта")
        self.resize(520, 480)

        self._build_ui()
        self._refresh_list()

    # =========================================================
    # DATA
    # =========================================================

    def _clone_project_data(self, pd):
        """Возвращает копию ProjectData (для отмены изменений)."""
        copy = ProjectData()
        for c in pd.characters.values():
            copy.characters[c.id] = Character.from_dict(c.to_dict())
        for v in pd.variables.values():
            copy.variables[v.id] = v
        for f in pd.flags.values():
            copy.flags[f.id] = f
        return copy

    def _apply_to_original(self):
        """Копирует изменения из _working в оригинал."""
        self.project_data.characters = self._working.characters
        # variables и flags не трогаем — они не редактируются тут

    # =========================================================
    # UI
    # =========================================================

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Персонажи проекта")
        title.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(title)

        hint = QLabel(
            "ID персонажа используется в узлах REPLY. "
            "Имя отображается в UI."
        )
        hint.setStyleSheet("color: #858B93; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # Список
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(
            self._on_edit_clicked
        )
        layout.addWidget(self.list_widget, 1)

        # Кнопки управления
        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(6)

        btn_add = QPushButton("+ Добавить")
        btn_add.clicked.connect(self._on_add_clicked)
        buttons.addWidget(btn_add)

        btn_edit = QPushButton("Редактировать")
        btn_edit.clicked.connect(self._on_edit_clicked)
        buttons.addWidget(btn_edit)

        btn_del = QPushButton("Удалить")
        btn_del.clicked.connect(self._on_delete_clicked)
        buttons.addWidget(btn_del)

        buttons.addStretch()
        layout.addLayout(buttons)

        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line2)

        # Нижние кнопки
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

    def _refresh_list(self):
        self.list_widget.clear()

        chars = sorted(
            self._working.characters.values(),
            key=lambda c: (c.name or c.id).lower(),
        )

        for c in chars:
            text = f"{c.name}  —  {c.id}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, c.id)
            self.list_widget.addItem(item)

        if not chars:
            placeholder = QListWidgetItem(
                "— нет персонажей. Нажмите «+ Добавить» —"
            )
            placeholder.setFlags(
                placeholder.flags() & ~Qt.ItemFlag.ItemIsSelectable
            )
            placeholder.setForeground(
                self.palette().placeholderText()
            )
            self.list_widget.addItem(placeholder)

    # =========================================================
    # HANDLERS
    # =========================================================

    def _current_id(self):
        item = self.list_widget.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_add_clicked(self):
        name, ok = QInputDialog.getText(
            self,
            "Новый персонаж",
            "Имя персонажа:",
        )

        if not ok:
            return

        name = name.strip()
        if not name:
            return

        from ..io.storage import _slugify
        char_id = _slugify(name)

        if not char_id:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось сформировать ID из имени.",
            )
            return

        if char_id in self._working.characters:
            QMessageBox.warning(
                self,
                "Конфликт",
                f"Персонаж с ID «{char_id}» уже существует.",
            )
            return

        char = Character(
            character_id=char_id,
            name=name,
        )
        self._working.add_character(char)
        self._refresh_list()

    def _on_edit_clicked(self):
        char_id = self._current_id()
        if not char_id:
            return

        char = self._working.get_character(char_id)
        if char is None:
            return

        new_name, ok = QInputDialog.getText(
            self,
            "Редактировать персонажа",
            f"Новое имя для «{char.name}» (ID: {char.id}):",
            text=char.name,
        )

        if not ok:
            return

        new_name = new_name.strip()
        if not new_name:
            return

        char.name = new_name
        self._refresh_list()

    def _on_delete_clicked(self):
        char_id = self._current_id()
        if not char_id:
            return

        char = self._working.get_character(char_id)
        if char is None:
            return

        reply = QMessageBox.question(
            self,
            "Удалить персонажа",
            f"Удалить «{char.name}» ({char.id})?\n"
            f"Узлы REPLY, ссылающиеся на него, "
            f"не изменятся — останется «мертвый» speaker_id.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self._working.remove_character(char_id)
        self._refresh_list()

    def _on_save_clicked(self):
        """Сохраняет project_data.json, применяет к оригиналу."""
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