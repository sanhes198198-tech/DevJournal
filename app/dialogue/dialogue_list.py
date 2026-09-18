"""
Левая панель редактора диалогов — список диалогов проекта.

Работает через io/storage.py — сам файловых операций не делает.
Все значимые действия эмитит сигналами наружу (в DialogueEditorWindow).
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QMessageBox,
    QFrame,
    QInputDialog,
)

from .io import (
    list_dialogue_ids,
    load_dialogue,
    load_index,
    save_index,
    delete_dialogue,
)


class DialogueList(QWidget):
    """Список диалогов в проекте."""

    # Эмитится, когда пользователь хочет открыть диалог
    dialogue_open_requested = Signal(str)   # dialogue_id

    # Эмитится, когда пользователь хочет создать новый диалог
    dialogue_new_requested = Signal()

    # Эмитится после успешного удаления файла
    dialogue_deleted = Signal(str)          # dialogue_id

    # Эмитится, когда пользователь хочет переименовать диалог
    dialogue_rename_requested = Signal(str, str)  # (dialogue_id, new_name)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.project_folder = None

        self._build_ui()

    # =========================================================
    # UI
    # =========================================================

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Заголовок
        title = QLabel("Диалоги")
        title.setStyleSheet(
            "font-weight: 600; font-size: 13px;"
        )
        layout.addWidget(title)

        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # Список
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(
            self._on_item_double_clicked
        )
        layout.addWidget(self.list_widget, 1)

        # Кнопки
        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(4)

        self.btn_new = QPushButton("+ Новый")
        self.btn_new.clicked.connect(self._on_new_clicked)
        buttons.addWidget(self.btn_new)

        self.btn_rename = QPushButton("Имя")
        self.btn_rename.clicked.connect(self._on_rename_clicked)
        buttons.addWidget(self.btn_rename)

        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        buttons.addWidget(self.btn_delete)

        layout.addLayout(buttons)

    # =========================================================
    # ПУБЛИЧНЫЙ API
    # =========================================================

    def set_project_folder(self, project_folder):
        """Устанавливает папку проекта и перечитывает список."""
        self.project_folder = project_folder
        self.refresh()

    def refresh(self):
        """Перечитывает index.json + перестраивает список."""
        self.list_widget.clear()

        if not self.project_folder:
            return

        ids = list_dialogue_ids(self.project_folder)
        index = load_index(self.project_folder)
        last_opened = index.get("last_opened")

        for i, dialogue_id in enumerate(ids):
            # Имя диалога: из файла, либо «Диалог N»
            try:
                dlg = load_dialogue(dialogue_id, self.project_folder)
                name = dlg.name if dlg and dlg.name else f"Диалог {i + 1}"
            except Exception:
                name = f"Диалог {i + 1}"

            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, dialogue_id)

            if dialogue_id == last_opened:
                item.setSelected(True)
                self.list_widget.setCurrentItem(item)

            self.list_widget.addItem(item)

    def current_dialogue_id(self):
        """ID выбранного диалога или None."""
        item = self.list_widget.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def select_dialogue(self, dialogue_id):
        """Программно выбрать диалог в списке."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == dialogue_id:
                self.list_widget.setCurrentItem(item)
                return

    def update_dialogue_name(self, dialogue_id, new_name):
        """Обновляет отображаемое имя диалога в списке (O(1))."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == dialogue_id:
                if new_name:
                    item.setText(new_name)
                else:
                    item.setText(f"Диалог {i + 1}")
                return

    # =========================================================
    # ОБРАБОТЧИКИ
    # =========================================================

    def _on_item_double_clicked(self, item):
        dialogue_id = item.data(Qt.ItemDataRole.UserRole)
        if dialogue_id:
            self.dialogue_open_requested.emit(dialogue_id)

    def _on_new_clicked(self):
        self.dialogue_new_requested.emit()

    def _on_rename_clicked(self):
        """Открывает диалог ввода нового имени."""
        item = self.list_widget.currentItem()
        if item is None:
            return

        dialogue_id = item.data(Qt.ItemDataRole.UserRole)
        if not dialogue_id:
            return

        current_name = item.text()

        new_name, ok = QInputDialog.getText(
            self,
            "Переименовать диалог",
            "Новое имя:",
            text=current_name,
        )

        if not ok:
            return

        new_name = new_name.strip()
        if not new_name or new_name == current_name:
            return

        self.dialogue_rename_requested.emit(dialogue_id, new_name)

    def _on_delete_clicked(self):
        dialogue_id = self.current_dialogue_id()

        if not dialogue_id:
            return

        # Подтверждение
        reply = QMessageBox.question(
            self,
            "Удалить диалог",
            f"Удалить диалог «{dialogue_id[:8]}...»?\n"
            f"Действие необратимо.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Удаляем файл
        try:
            delete_dialogue(dialogue_id, self.project_folder)
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось удалить файл: {exc!r}",
            )
            return

        # Обновляем index.json
        try:
            index = load_index(self.project_folder)

            ids = index.get("dialogue_ids", [])
            if dialogue_id in ids:
                ids.remove(dialogue_id)
            index["dialogue_ids"] = ids

            if index.get("last_opened") == dialogue_id:
                index["last_opened"] = None

            save_index(index, self.project_folder)
        except Exception:
            pass

        self.refresh()
        self.dialogue_deleted.emit(dialogue_id)
