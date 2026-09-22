"""
Макет архитектурного модуля (план B).

Без логики — только раскладка UI:

    [Тулбар]
    [Вкладки режимов: Сцена | VE | Constructor]
    [Левая панель | Канвас с 4 проекциями | Правая панель]
    [Статусбар]

Позже:
  - вкладка "Сцена"       → реальная сцена (размещение зданий, экспорт)
  - вкладка "VE"          → встроенный VectorEditor
  - вкладка "Constructor" → встроенный конструктор композитов
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QListWidget,
    QMainWindow,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)


class ArchitectureMockup(QMainWindow):
    """Макет окна Architecture — только раскладка, без логики."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Архитектура — макет")
        self.resize(1600, 900)

        self._build_toolbar()
        self._build_central()
        self._build_statusbar()

    # ------------------------------------------------------------------
    # TOOLBAR
    # ------------------------------------------------------------------

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main", self)
        tb.setMovable(False)
        self.addToolBar(tb)

        for label in ("Новый", "Открыть", "Сохранить"):
            tb.addAction(QAction(label, self))

        tb.addSeparator()

        for label in ("Отменить", "Повторить"):
            tb.addAction(QAction(label, self))

        tb.addSeparator()

        for label in ("Удалить", "Дублировать"):
            tb.addAction(QAction(label, self))

        tb.addSeparator()

        act_export = QAction("Экспорт ▼", self)
        act_export.setToolTip(
            "Экспорт сцены в Blender (glTF / FBX) — пока заглушка"
        )
        tb.addAction(act_export)

    # ------------------------------------------------------------------
    # CENTRAL — вкладки режимов
    # ------------------------------------------------------------------

    def _build_central(self) -> None:
        self._mode_tabs = QTabWidget()
        self._mode_tabs.setDocumentMode(True)

        # Контейнеры под встроенные модули
        self._ve_container = QWidget()
        self._ve_layout = QVBoxLayout(self._ve_container)
        self._ve_layout.setContentsMargins(0, 0, 0, 0)

        self._constructor_container = QWidget()
        self._constructor_layout = QVBoxLayout(
            self._constructor_container
        )
        self._constructor_layout.setContentsMargins(0, 0, 0, 0)

        # Ссылки на встроенные модули (None = ещё не созданы)
        self._ve_embedded = None
        self._constructor_embedded = None

        self._mode_tabs.addTab(self._build_scene_tab(), "🏗  Сцена")
        self._mode_tabs.addTab(self._ve_container, "✏  VE")
        self._mode_tabs.addTab(
            self._constructor_container, "🧱  Constructor"
        )

        self._mode_tabs.currentChanged.connect(self._on_tab_changed)

        self.setCentralWidget(self._mode_tabs)

    # ------------------------------------------------------------------
    # SCENE TAB — левая панель / канвас / правая панель
    # ------------------------------------------------------------------

    def _build_scene_tab(self) -> QWidget:
        splitter = QSplitter(Qt.Orientation.Horizontal)

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_center_projections())
        splitter.addWidget(self._build_right_panel())

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setCollapsible(2, False)

        return splitter

    def _build_left_panel(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(240)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        layout.addWidget(self._section_label("Здания"))
        buildings = QListWidget()
        buildings.addItems([
            "Сторожевая башня",
            "Крепостная стена",
            "Ворота",
            "Дом",
        ])
        layout.addWidget(buildings)

        layout.addWidget(self._section_label("Декор"))
        decor = QListWidget()
        decor.addItems(["Дерево", "Фонарь", "Куст"])
        decor.setMaximumHeight(90)
        layout.addWidget(decor)

        layout.addWidget(self._section_label("Слои сцены"))
        layers = QListWidget()
        layers.addItems([
            "🌍 Земля",
            "🏰 Здания",
            "🌳 Декор",
            "🪨 Руины",
        ])
        layers.setMaximumHeight(120)
        layout.addWidget(layers)

        layout.addStretch()

        hint = QLabel(
            "Здания создаются в Constructor.\n"
            "Перетащи на сцену → появится инстанс."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(hint)

        return w

    def _build_center_projections(self) -> QTabWidget:
        tabs = QTabWidget()
        for name in ("План", "Фасад", "Разрез", "3D"):
            tabs.addTab(self._canvas_placeholder(name), name)
        return tabs

    def _build_right_panel(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(260)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        layout.addWidget(self._section_label("Свойства"))

        hint = QLabel("Ничего не выбрано.")
        hint.setStyleSheet("color: #888;")
        layout.addWidget(hint)

        layout.addStretch()
        return w

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "font-weight: 600; font-size: 11px; "
            "color: #1A1A1A; padding-top: 6px;"
        )
        return lbl

    @staticmethod
    def _canvas_placeholder(name: str) -> QLabel:
        lbl = QLabel(f"[{name}] — сюда будет рендериться сцена")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(
            "background: #FAFAFA; color: #888; "
            "font-size: 14px; border: 1px solid #DDD;"
        )
        return lbl

    @staticmethod
    def _placeholder(title: str, text: str) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addStretch()

        t = QLabel(title)
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet("font-size: 22px; font-weight: 600;")
        layout.addWidget(t)

        d = QLabel(text)
        d.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d.setStyleSheet("color: #666; font-size: 13px;")
        layout.addWidget(d)

        layout.addStretch()
        return w

    # ------------------------------------------------------------------
    # STATUS BAR
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # MODULE TABS — кнопка запуска + описание
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # LAZY EMBED — VE / Constructor
    # ------------------------------------------------------------------

    def _on_tab_changed(self, index: int) -> None:
        """При переключении вкладки — ленивая инициализация модуля."""
        if index == 1:
            self._ensure_ve_embedded()
        elif index == 2:
            self._ensure_constructor_embedded()

    def _ensure_ve_embedded(self) -> None:
        """Создать VectorEditor и встроить окно целиком (тулбар+панели)."""
        if self._ve_embedded is not None:
            return

        try:
            from app.vector_editor.editor import VectorEditor
        except Exception as e:
            self._embed_error(self._ve_layout, "VE", e)
            self._ve_embedded = "error"
            return

        try:
            editor = VectorEditor()
            self._embed_window(self._ve_layout, editor)
            self._ve_embedded = editor
        except Exception as e:
            self._embed_error(self._ve_layout, "VE", e)
            self._ve_embedded = "error"

    def _ensure_constructor_embedded(self) -> None:
        """Создать ConstructorWindow и встроить окно целиком."""
        if self._constructor_embedded is not None:
            return

        try:
            from app.constructor.constructor_window import (
                ConstructorWindow,
            )
        except Exception as e:
            self._embed_error(
                self._constructor_layout, "Constructor", e
            )
            self._constructor_embedded = "error"
            return

        try:
            ctor = ConstructorWindow()
            self._embed_window(self._constructor_layout, ctor)
            self._constructor_embedded = ctor
        except Exception as e:
            self._embed_error(
                self._constructor_layout, "Constructor", e
            )
            self._constructor_embedded = "error"

    @staticmethod
    def _embed_window(layout, window) -> None:
        """Встроить QMainWindow как виджет в layout вкладки."""
        window.setWindowFlags(Qt.WindowType.Widget)
        window.setWindowTitle("")
        layout.addWidget(window)

    @staticmethod
    def _embed_error(layout, name: str, exc: Exception) -> None:
        """Показать ошибку встраивания внутри вкладки."""
        msg = QLabel(
            f"Не удалось встроить модуль {name}.\n\n"
            f"{type(exc).__name__}: {exc}"
        )
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setWordWrap(True)
        msg.setStyleSheet("color: #C00; font-size: 13px; padding: 20px;")
        layout.addWidget(msg)

    # ------------------------------------------------------------------
    # MODULE TABS (старый вариант — кнопки, больше не используется)
    # ------------------------------------------------------------------

    def _build_module_tab(self, title: str, desc: str, opener) -> QWidget:
        """Вкладка с кнопкой запуска отдельного QMainWindow-модуля."""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addStretch()

        t = QLabel(title)
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet("font-size: 22px; font-weight: 600;")
        layout.addWidget(t)

        d = QLabel(desc)
        d.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d.setStyleSheet("color: #666; font-size: 13px;")
        layout.addWidget(d)

        btn = QPushButton("Открыть в отдельном окне")
        btn.setFixedWidth(280)
        btn.clicked.connect(opener)

        btn_row = QWidget()
        btn_layout = QVBoxLayout(btn_row)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(btn_row)

        note = QLabel(
            "Позже модуль будет встроен прямо в эту вкладку."
        )
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setStyleSheet(
            "color: #AAA; font-size: 11px; padding-top: 12px;"
        )
        layout.addWidget(note)

        layout.addStretch()
        return w

    def _open_ve(self) -> None:
        """Открыть VectorEditor в отдельном окне."""
        existing = getattr(self, "_ve_window", None)
        if existing is None:
            from app.vector_editor.editor import VectorEditor
            self._ve_window = VectorEditor()
        self._ve_window.show()
        self._ve_window.raise_()
        self._ve_window.activateWindow()

    def _open_constructor(self) -> None:
        """Открыть ConstructorWindow в отдельном окне."""
        existing = getattr(self, "_constructor_window", None)
        if existing is None:
            from app.constructor.constructor_window import ConstructorWindow
            self._constructor_window = ConstructorWindow()
        self._constructor_window.show()
        self._constructor_window.raise_()
        self._constructor_window.activateWindow()

    def _build_statusbar(self) -> None:
        sb = QStatusBar(self)
        sb.showMessage(
            "Сетка 1м · Snap вкл · X=0.0 Y=0.0 · Масштаб 100%"
        )
        self.setStatusBar(sb)
