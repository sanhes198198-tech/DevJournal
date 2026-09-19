"""
ArchitectureEditor — QMainWindow архитектурного редактора.

Компоновка:
    ┌─────────────────────────────────────────┐
    │ Тулбар: [Сохранить]                     │
    ├──────────┬─────────────────┬────────────┤
    │ Палитра  │ ModeTabs        │ Свойства   │
    │          ├─────────────────┤            │
    │          │                 │            │
    │          │     Canvas      │            │
    │          │                 │            │
    └──────────┴─────────────────┴────────────┘
    │ Статус-бар                              │
    └─────────────────────────────────────────┘

Вход:
    ArchitectureEditor.open_for_project(project_folder) -> editor | None
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .architecture_document import ArchitectureDocument
from .io import (
    StorageError,
    get_architecture_path,
)
from .view import (
    ArchScene,
    ArchCanvas,
    PalettePanel,
    PropertiesPanel,
    ModeTabs,
)


class ArchitectureEditor(QMainWindow):
    """Окно архитектурного редактора."""

    def __init__(self, document: ArchitectureDocument, parent=None):
        super().__init__(parent)

        self._document = document

        self._build_ui()
        self._connect_signals()
        self._update_title()
        self._update_save_action_state()

    # ============================================================
    # ФАБРИКА
    # ============================================================

    @classmethod
    def open_for_project(
        cls,
        project_folder: Path,
        parent=None,
    ) -> "ArchitectureEditor | None":
        """Открывает редактор для папки проекта.

        Загружает существующий architecture.json или создаёт новый
        документ (файл на диск не пишется до первого save).

        Возвращает None при ошибке загрузки — вызывающий решает,
        что делать.
        """
        # ensure_project_folder может вернуть str — нормализуем
        project_folder = Path(project_folder)

        arch_path = get_architecture_path(project_folder)

        if arch_path.exists():
            try:
                doc = ArchitectureDocument.load(arch_path)
            except StorageError as e:
                QMessageBox.critical(
                    parent,
                    "Ошибка загрузки архитектуры",
                    "Не удалось загрузить architecture.json:\n\n"
                    f"{e}\n\n"
                    "Файл будет открыт без изменений. "
                    "Проверьте его вручную.",
                )
                return None
        else:
            name = f"Архитектура — {project_folder.name}"
            doc = ArchitectureDocument.create_new(arch_path, name=name)

        return cls(doc, parent=parent)

    # ============================================================
    # PROPERTIES
    # ============================================================

    @property
    def document(self) -> ArchitectureDocument:
        return self._document

    @property
    def project_folder(self) -> Path | None:
        """Папка проекта, к которой привязан документ.

        Используется внешним кодом (window.py) для singleton-логики.
        """
        if self._document.path is None:
            return None
        return self._document.path.parent

    # ============================================================
    # UI
    # ============================================================

    def _build_ui(self) -> None:
        self.resize(1400, 900)

        self._build_toolbar()
        self._build_central()
        self._build_status_bar()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Основное", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._action_save = QAction("Сохранить", self)
        self._action_save.setShortcut(QKeySequence.StandardKey.Save)
        self._action_save.triggered.connect(self._on_save)
        toolbar.addAction(self._action_save)

        toolbar.addSeparator()

        action_close = QAction("Закрыть", self)
        action_close.triggered.connect(self.close)
        toolbar.addAction(action_close)

    def _build_central(self) -> None:
        # Scene + Canvas
        self._scene = ArchScene(self._document)
        self._canvas = ArchCanvas(self._scene)

        # Центральная колонка: ModeTabs над Canvas
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        self._mode_tabs = ModeTabs()
        center_layout.addWidget(self._mode_tabs)
        center_layout.addWidget(self._canvas, 1)

        # Панели
        self._palette = PalettePanel()
        self._properties = PropertiesPanel()

        # Splitter: palette | center | properties
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._palette)
        splitter.addWidget(center)
        splitter.addWidget(self._properties)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setCollapsible(2, False)

        self.setCentralWidget(splitter)

    def _build_status_bar(self) -> None:
        self.statusBar().showMessage("Готово")

    # ============================================================
    # СИГНАЛЫ
    # ============================================================

    def _connect_signals(self) -> None:
        self._document.modified_changed.connect(
            self._on_modified_changed
        )
        self._mode_tabs.mode_changed.connect(
            self._on_mode_changed
        )

    def _on_modified_changed(self, modified: bool) -> None:
        self._update_title()
        self._update_save_action_state()

    def _on_mode_changed(self, mode: str) -> None:
        self.statusBar().showMessage(f"Режим: {mode}", 2000)

    # ============================================================
    # TITLE / ACTIONS
    # ============================================================

    def _update_title(self) -> None:
        name = self._document.model.meta.get("name", "Архитектура")
        star = " *" if self._document.is_modified() else ""
        self.setWindowTitle(f"{name}{star} — Архитектура")

    def _update_save_action_state(self) -> None:
        self._action_save.setEnabled(self._document.is_modified())

    def _on_save(self) -> None:
        try:
            self._document.save()
        except StorageError as e:
            QMessageBox.critical(
                self,
                "Ошибка сохранения",
                f"Не удалось сохранить architecture.json:\n\n{e}",
            )
            return

        self.statusBar().showMessage("Сохранено", 2000)

    # ============================================================
    # CLOSE
    # ============================================================

    def closeEvent(self, event) -> None:
        if not self._document.is_modified():
            event.accept()
            return

        name = self._document.model.meta.get("name", "Архитектура")

        result = QMessageBox.question(
            self,
            "Несохранённые изменения",
            f"Сохранить изменения в «{name}»?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )

        if result == QMessageBox.StandardButton.Save:
            try:
                self._document.save()
            except StorageError as e:
                QMessageBox.critical(
                    self,
                    "Ошибка сохранения",
                    f"Не удалось сохранить:\n\n{e}",
                )
                event.ignore()
                return
            event.accept()

        elif result == QMessageBox.StandardButton.Discard:
            event.accept()

        else:
            event.ignore()
