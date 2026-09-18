"""
Окно редактора диалогов.

Компоновка:
┌─────────────────────────────────────────────────────┐
│ Toolbar: Save / Undo / Redo / Validate / New        │
├──────────────┬──────────────────────┬───────────────┤
│              │                      │               │
│ DialogueList │     DialogueView     │  Inspector    │
│              │                      │               │
├──────────────┴──────────────────────┴───────────────┤
│ Status                                              │
└─────────────────────────────────────────────────────┘

Окно связывает компоненты, но НЕ хранит бизнес-логику.
Файловые операции — через io/storage.py.
Undo/redo — через commands.
Валидация — через validation.
"""

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QUndoStack, QShortcut, QKeySequence, QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QSplitter,
    QToolBar,
    QMessageBox,
    QLabel,
)

from .dialogue_list import DialogueList
from .view import DialogueView, DialogueInspector

from .ids import (
    generate_dialogue_id,
    generate_node_id,
)

from .model import (
    Dialogue,
    StartNode,
    EndNode,
)

from .io import (
    save_dialogue,
    load_dialogue,
    load_index,
    save_index,
    dialogue_exists,
)

from .validation import validate_dialogue
from .commands import ChangePropertyCommand


class DialogueEditorWindow(QMainWindow):
    """Отдельное окно редактора диалогов."""

    def __init__(self, project_folder, parent=None):
        super().__init__(parent)

        self.project_folder = project_folder

        # Текущий загруженный диалог (Dialogue или None)
        self.current_dialogue = None

        # Undo stack
        self.undo_stack = QUndoStack(self)
        self.undo_stack.cleanChanged.connect(self._on_clean_changed)

        self.setWindowTitle("Диалоги — DevJournal")
        self.resize(1400, 900)

        self._build_ui()
        self._connect_signals()
        self._setup_shortcuts()

        # Авто-открытие последнего диалога
        self._open_last_dialogue_if_any()

    # =========================================================
    # UI
    # =========================================================

    def _build_ui(self):
        # Toolbar
        toolbar = QToolBar("Основные")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        act_new = QAction("+ Новый", self)
        act_new.triggered.connect(self.new_dialogue)
        toolbar.addAction(act_new)

        act_save = QAction("Сохранить", self)
        act_save.triggered.connect(self.save_current)
        toolbar.addAction(act_save)

        toolbar.addSeparator()

        act_undo = QAction("Отменить", self)
        act_undo.triggered.connect(self.undo_stack.undo)
        toolbar.addAction(act_undo)

        act_redo = QAction("Повторить", self)
        act_redo.triggered.connect(self.undo_stack.redo)
        toolbar.addAction(act_redo)

        toolbar.addSeparator()

        act_validate = QAction("Проверить", self)
        act_validate.triggered.connect(self.validate_current)
        toolbar.addAction(act_validate)

        toolbar.addSeparator()

        act_fit = QAction("Zoom fit", self)
        act_fit.triggered.connect(
            lambda: self.view.zoom_to_fit()
        )
        toolbar.addAction(act_fit)

        act_find = QAction("Найти", self)
        act_find.triggered.connect(
            lambda: self.view.find_node_dialog()
        )
        toolbar.addAction(act_find)

        # Центральный виджет
        central = QWidget()
        layout = QSplitter(Qt.Orientation.Horizontal)

        self.dialogue_list = DialogueList()
        self.dialogue_list.setFixedWidth(240)

        self.view = DialogueView()
        self.inspector = DialogueInspector()

        layout.addWidget(self.dialogue_list)
        layout.addWidget(self.view)
        layout.addWidget(self.inspector)

        layout.setStretchFactor(0, 0)
        layout.setStretchFactor(1, 3)
        layout.setStretchFactor(2, 1)
        layout.setSizes([240, 900, 300])

        central.setLayout(_wrap_splitter_in_layout(layout))

        self.setCentralWidget(central)

        # Status bar
        self.status_label = QLabel("Готово")
        self.statusBar().addWidget(self.status_label)

    # =========================================================
    # СИГНАЛЫ
    # =========================================================

    def _connect_signals(self):
        # List → Editor
        self.dialogue_list.dialogue_open_requested.connect(
            self.load_dialogue
        )
        self.dialogue_list.dialogue_new_requested.connect(
            self.new_dialogue
        )
        self.dialogue_list.dialogue_deleted.connect(
            self._on_dialogue_deleted
        )

        self.dialogue_list.dialogue_rename_requested.connect(
            self._on_dialogue_rename_requested
        )

        # Inspector → View
        self.inspector.node_changed.connect(self._on_inspector_node_changed)
        self.inspector.connections_changed.connect(
            self._on_inspector_connections_changed
        )

        # Inspector command sink
        self.inspector.set_command_sink(self.undo_stack.push)

        # Scene command sink (для ПКМ-создания узлов, макросов и т.д.)
        self.view.dialogue_scene.set_command_sink(
            self.undo_stack.push,
            undo_stack=self.undo_stack,
        )

        # View → Inspector
        self.view.dialogue_scene.selectionChanged.connect(
            self._on_selection_changed
        )

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_current)
        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo_stack.undo)
        QShortcut(
            QKeySequence("Ctrl+Shift+Z"),
            self,
            self.undo_stack.redo,
        )
        QShortcut(QKeySequence("Ctrl+Y"), self, self.undo_stack.redo)
        QShortcut(QKeySequence("Ctrl+N"), self, self.new_dialogue)

        # Ctrl+0 — zoom to fit (на уровне окна, чтобы не конфликтовать с главным)
        QShortcut(
            QKeySequence("Ctrl+0"),
            self,
            self._on_zoom_fit_shortcut,
        )

        # Ctrl+F — поиск
        QShortcut(
            QKeySequence("Ctrl+F"),
            self,
            self._on_find_shortcut,
        )

    def _on_zoom_fit_shortcut(self):
        try:
            self.view.zoom_to_fit()
        except Exception:
            pass

    def _on_find_shortcut(self):
        try:
            self.view.find_node_dialog()
        except Exception:
            pass

    # =========================================================
    # ПУБЛИЧНЫЙ API
    # =========================================================

    def load_dialogue(self, dialogue_id):
        """Загружает диалог по id."""
        if not dialogue_id:
            return

        if not dialogue_exists(dialogue_id, self.project_folder):
            self._set_status(f"Диалог {dialogue_id[:8]}... не найден")
            return

        dlg = load_dialogue(dialogue_id, self.project_folder)

        if dlg is None:
            self._set_status("Ошибка загрузки диалога")
            return

        self.current_dialogue = dlg

        # Загрузка в view
        self.view.rebuild_from_model(dlg)

        # Inspector
        self.inspector.set_dialogue(dlg)
        self.inspector.clear()

        # Сброс undo (иначе Ctrl+Z из другого диалога сломает)
        self.undo_stack.clear()
        self.undo_stack.setClean()

        # Обновить список + title
        self.dialogue_list.select_dialogue(dialogue_id)
        self._update_index_last_opened(dialogue_id)
        self._update_window_title()

        self._set_status(f"Загружен: {dlg.name or dialogue_id[:8]}")

    def new_dialogue(self):
        """Создаёт новый диалог с Start + End."""
        dlg_id = generate_dialogue_id()

        dlg = Dialogue(
            dialogue_id=dlg_id,
            name="Новый диалог",
            description="",
        )

        start = StartNode(generate_node_id(), x=0, y=0)
        end = EndNode(generate_node_id(), x=400, y=0)

        dlg.add_node(start)
        dlg.add_node(end)

        # Сразу сохраняем на диск
        try:
            save_dialogue(dlg, self.project_folder)
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось сохранить диалог: {exc!r}",
            )
            return

        # Обновляем index
        self._add_to_index(dlg_id)

        # Перестраиваем список
        self.dialogue_list.refresh()

        # Загружаем
        self.load_dialogue(dlg_id)

    def save_current(self):
        """Сохраняет текущий диалог."""
        if self.current_dialogue is None:
            self._set_status("Нет открытого диалога")
            return

        # Синхронизируем позиции узлов в модели (страховка)
        try:
            self.view.sync_positions_to_model()
        except Exception:
            pass

        try:
            save_dialogue(self.current_dialogue, self.project_folder)
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось сохранить: {exc!r}",
            )
            return

        self.undo_stack.setClean()

        # Обновим имя в списке (если было изменено)
        self.dialogue_list.refresh()

        self._set_status("Сохранено", timeout_ms=3000)

    def validate_current(self):
        """Валидирует диалог и показывает диалог с навигацией."""
        if self.current_dialogue is None:
            self._set_status("Нет открытого диалога")
            return

        # Известные ID диалогов проекта (для cross-dialogue проверки)
        try:
            from .io import list_dialogue_ids
            known_ids = list_dialogue_ids(self.project_folder)
        except Exception:
            known_ids = None

        result = validate_dialogue(
            self.current_dialogue,
            known_dialogue_ids=known_ids,
        )

        # Строим карту node_id -> человекочитаемое имя
        node_labels = {}
        for node in self.current_dialogue.nodes.values():
            if node.type == "reply":
                speaker = getattr(node, "speaker", "") or ""
                text = getattr(node, "text", "") or ""
                preview = (text[:30] + "...") if len(text) > 30 else text
                label = f"REPLY {speaker} \u00ab{preview}\u00bb".strip()
            elif node.type == "choice":
                q = getattr(node, "question", "") or "(без вопроса)"
                preview = (q[:30] + "...") if len(q) > 30 else q
                label = f"CHOICE \u00ab{preview}\u00bb"
            elif node.type == "start":
                label = "START"
            elif node.type == "end":
                label = "END"
            else:
                label = node.type.upper()

            node_labels[node.id] = label

        # Открываем диалог
        from .view import ValidationDialog

        dlg = ValidationDialog(
            result=result,
            node_labels=node_labels,
            parent=self,
        )

        dlg.exec()

        # Если пользователь выбрал узел — центрируем
        if dlg.selected_node_id:
            item = self.view.dialogue_scene.node_items.get(
                dlg.selected_node_id
            )
            if item is not None:
                self.view.dialogue_scene.clearSelection()
                item.setSelected(True)
                self.view.centerOn(item)
                self.view.setFocus()

    def _on_selection_changed(self):
        """Выделение в сцене → Inspector."""
        selected = self.view.dialogue_scene.selectedItems()

        node_item = None
        for item in selected:
            if hasattr(item, "node_id"):
                node_item = item
                break

        if node_item is None:
            self.inspector.clear()
        else:
            self.inspector.set_node(node_item.node_id)

    def _on_inspector_node_changed(self, node_id):
        """Inspector изменил текст/вопрос — легкое обновление узла."""
        node_item = self.view.dialogue_scene.get_node_item(node_id)
        if node_item is not None:
            node_item.refresh_text_only()

    def _on_inspector_connections_changed(self):
        """Порты изменились — пересобираем view + сохраняем выделение."""
        selected_id = self.inspector.current_node_id

        scene = self.view.dialogue_scene
        scene.blockSignals(True)

        try:
            self.view.rebuild_from_model(self.current_dialogue)

            if selected_id:
                item = scene.get_node_item(selected_id)
                if item is not None:
                    item.setSelected(True)
        finally:
            scene.blockSignals(False)

        self.view.viewport().update()

        if selected_id:
            self.inspector.set_node(selected_id)
        else:
            self.inspector.clear()

    def _on_dialogue_deleted(self, dialogue_id):
        """Диалог удалён — если это текущий, очищаем редактор."""
        if (
            self.current_dialogue is not None
            and self.current_dialogue.id == dialogue_id
        ):
            self.current_dialogue = None
            self.view.rebuild_from_model(None)
            self.inspector.clear()
            self.undo_stack.clear()
            self._update_window_title()

    def _on_dialogue_rename_requested(self, dialogue_id, new_name):
        """Переименовать диалог (через ChangePropertyCommand)."""
        if not dialogue_id or not new_name:
            return

        # Если это не текущий — сначала загружаем
        if (
            self.current_dialogue is None
            or self.current_dialogue.id != dialogue_id
        ):
            self.load_dialogue(dialogue_id)

        if self.current_dialogue is None:
            return

        old_name = self.current_dialogue.name
        if old_name == new_name:
            return

        def _notify():
            self.dialogue_list.update_dialogue_name(
                dialogue_id, new_name
            )
            self._update_window_title()

        cmd = ChangePropertyCommand(
            target=self.current_dialogue,
            prop_name="name",
            old_value=old_name,
            new_value=new_name,
            notify=_notify,
        )
        self.undo_stack.push(cmd)

    def _on_clean_changed(self, is_clean):
        """Обновляет суффикс в заголовке окна."""
        self._update_window_title()

    # =========================================================
    # ВСПОМОГАТЕЛЬНОЕ
    # =========================================================

    def _update_window_title(self):
        if self.current_dialogue is None:
            suffix = ""
        else:
            suffix = f" — {self.current_dialogue.name or self.current_dialogue.id[:8]}"
            if not self.undo_stack.isClean():
                suffix += " *"

        self.setWindowTitle(f"Диалоги{suffix} — DevJournal")

    def _set_status(self, text, timeout_ms=0):
        self.status_label.setText(text)

        if timeout_ms:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(
                timeout_ms,
                lambda: self.status_label.setText("Готово"),
            )

    def _update_index_last_opened(self, dialogue_id):
        try:
            index = load_index(self.project_folder)
            index["last_opened"] = dialogue_id
            save_index(index, self.project_folder)
        except Exception:
            pass

    def _add_to_index(self, dialogue_id):
        try:
            index = load_index(self.project_folder)
            ids = index.get("dialogue_ids", [])

            if dialogue_id not in ids:
                ids.append(dialogue_id)

            index["dialogue_ids"] = ids
            index["last_opened"] = dialogue_id

            save_index(index, self.project_folder)
        except Exception:
            pass

    def _open_last_dialogue_if_any(self):
        """Открывает последний диалог проекта (если есть)."""
        self.dialogue_list.set_project_folder(self.project_folder)

        try:
            index = load_index(self.project_folder)
            last_opened = index.get("last_opened")
        except Exception:
            last_opened = None

        if last_opened and dialogue_exists(last_opened, self.project_folder):
            self.load_dialogue(last_opened)

    # =========================================================
    # ЗАКРЫТИЕ
    # =========================================================

    def closeEvent(self, event):
        """При закрытии — спрашиваем сохранить, если есть несохранённое."""
        if (
            self.current_dialogue is not None
            and not self.undo_stack.isClean()
        ):
            reply = QMessageBox.question(
                self,
                "Несохранённые изменения",
                "Сохранить изменения перед закрытием?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes,
            )

            if reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return

            if reply == QMessageBox.StandardButton.Yes:
                self.save_current()

        event.accept()


# =========================================================
# ХЕЛПЕР
# =========================================================

def _wrap_splitter_in_layout(splitter):
    """Оборачивает QSplitter в QVBoxLayout, чтобы вставить в QWidget."""
    from PySide6.QtWidgets import QVBoxLayout

    layout = QVBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.addWidget(splitter)

    return layout
