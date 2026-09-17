"""
Удаление проектов DevJournal.

Модуль полностью изолирован:
- содержит диалог выбора проекта;
- содержит логику безопасного удаления папки проекта;
- не изменяет существующие new_project / open_project / save_project.

Единственная точка входа: delete_project_dialog(window).
"""

import os
import shutil

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from .config import BOARDS_DIR


# ============================================================
# HELPERS
# ============================================================

def _list_projects():
    """
    Возвращает отсортированный список папок-проектов в boards/.
    """

    if not os.path.isdir(BOARDS_DIR):
        return []

    try:
        entries = os.listdir(BOARDS_DIR)
    except OSError:
        return []

    projects = []

    for name in entries:
        full = os.path.join(BOARDS_DIR, name)

        if not os.path.isdir(full):
            continue

        projects.append(name)

    projects.sort(key=str.lower)

    return projects


def _format_size(num_bytes):
    """
    Человекочитаемый размер.
    """

    size = float(num_bytes)

    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0

    return f"{size:.1f} ТБ"


def _folder_size(folder):
    """
    Считает суммарный размер файлов в папке.
    """

    total = 0

    for root, _dirs, files in os.walk(folder):
        for name in files:
            path = os.path.join(root, name)

            try:
                total += os.path.getsize(path)
            except OSError:
                pass

    return total


# ============================================================
# DIALOG
# ============================================================

class DeleteProjectDialog(QDialog):
    """
    Диалог выбора и удаления проекта.
    """

    def __init__(self, window, parent=None):
        super().__init__(parent or window)

        self.window = window

        self.setWindowTitle(
            "Удаление проекта"
        )

        self.setMinimumWidth(
            440
        )

        self.setMinimumHeight(
            340
        )

        self._build_ui()
        self._reload()

    # --------------------------------------------------------

    def _build_ui(self):

        layout = QVBoxLayout(self)

        layout.addWidget(
            QLabel("Выберите проект для удаления:")
        )

        self.list_widget = QListWidget()

        self.list_widget.currentItemChanged.connect(
            self._on_selection_changed
        )

        layout.addWidget(
            self.list_widget,
            1,
        )

        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)

        layout.addWidget(
            self.info_label
        )

        buttons_row = QHBoxLayout()

        self.delete_button = QPushButton(
            "Удалить"
        )

        self.delete_button.setEnabled(False)

        cancel_button = QPushButton(
            "Отмена"
        )

        self.delete_button.clicked.connect(
            self._on_delete_clicked
        )

        cancel_button.clicked.connect(
            self.reject
        )

        buttons_row.addStretch(1)
        buttons_row.addWidget(cancel_button)
        buttons_row.addWidget(self.delete_button)

        layout.addLayout(buttons_row)

    # --------------------------------------------------------

    def _reload(self):

        self.list_widget.clear()

        current = getattr(
            self.window,
            "project_name",
            None,
        )

        projects = _list_projects()

        for name in projects:

            label = name

            if name == current:
                label = f"{name}   (текущий)"

            item = QListWidgetItem(label)

            item.setData(
                Qt.ItemDataRole.UserRole,
                name,
            )

            self.list_widget.addItem(item)

        if self.list_widget.count() == 0:

            self.info_label.setText(
                "Нет доступных проектов для удаления."
            )

            self.delete_button.setEnabled(False)

            return

        self.list_widget.setCurrentRow(0)

    # --------------------------------------------------------

    def _selected_project(self):

        item = self.list_widget.currentItem()

        if item is None:
            return None

        return item.data(
            Qt.ItemDataRole.UserRole
        )

    # --------------------------------------------------------

    def _on_selection_changed(self, *_):

        name = self._selected_project()

        if not name:
            self.delete_button.setEnabled(False)
            self.info_label.setText("")
            return

        folder = os.path.join(
            BOARDS_DIR,
            name,
        )

        try:
            size_text = _format_size(
                _folder_size(folder)
            )
        except Exception:
            size_text = "?"

        is_current = (
            name
            == getattr(
                self.window,
                "project_name",
                None,
            )
        )

        marker = (
            "\n⚠ Это текущий открытый проект. "
            "Он будет закрыт."
            if is_current
            else ""
        )

        self.info_label.setText(
            f"Папка: {folder}\n"
            f"Размер: {size_text}"
            f"{marker}"
        )

        self.delete_button.setEnabled(True)

    # --------------------------------------------------------

    def _on_delete_clicked(self):

        name = self._selected_project()

        if not name:
            return

        answer = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Удалить проект «{name}»?\n\n"
            "Все карточки, изображения и файлы проекта "
            "будут удалены безвозвратно.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        folder = os.path.join(
            BOARDS_DIR,
            name,
        )

        try:
            shutil.rmtree(folder)
        except Exception as exc:

            QMessageBox.critical(
                self,
                "Ошибка удаления",
                f"Не удалось удалить проект:\n{exc}",
            )

            return

        is_current = (
            name
            == getattr(
                self.window,
                "project_name",
                None,
            )
        )

        if is_current:
            self._reset_current_project()

        self._reload()

        try:
            self.window.status_label.setText(
                f"Проект «{name}» удалён"
            )
        except Exception:
            pass

    # --------------------------------------------------------

    def _reset_current_project(self):
        """
        Если удалили текущий проект, сбрасываем окно в
        состояние «проект не выбран».
        """

        window = self.window

        try:
            window.canvas.scene.clear()
        except Exception:
            pass

        try:
            window.project_name = None
        except Exception:
            pass

        try:
            if window.project_name_label is not None:
                window.project_name_label.setText("")
        except Exception:
            pass

        try:
            window.last_selected_item = None
        except Exception:
            pass


# ============================================================
# ENTRY POINT
# ============================================================

def delete_project_dialog(window):
    """
    Открывает диалог удаления проекта.
    """

    dialog = DeleteProjectDialog(
        window,
        parent=window,
    )

    dialog.exec()