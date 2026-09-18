import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QToolButton,
    QFileDialog,
    QMessageBox,
    QInputDialog,
    QApplication,
    QGraphicsTextItem,
)

from .config import APP_NAME, BOARDS_DIR
from .window_styles import QSS
from .window_sidebar import build_sidebar
from .top_navigation_panel import TopNavigationPanel
from .window_format_toolbar import FormatToolbar
from .window_format_toolbar_controller import FormatToolbarController
from .utils import safe_project_name, ensure_project_folder
from .canvas import Canvas
from .canvas.color import _show_color_palette
from .settings import SettingsDialog
from .cards.text.text_card import TextCard
from .cards.heading.heading_card import HeadingCard
from .cards.image_text.image_card import ImageTextCard
from .cards.comment.comment_card import CommentCard
from .cards.video.video_text_item import VideoTextItem
from .items.arrow_follow import ArrowFollowManager


class DevJournal(QMainWindow):

    def __init__(self):
        super().__init__()

        self.project_name = ""
        self.project_file_path = ""
        self.last_selected_item = None
        self.active_text_item = None

        # Активный раздел проекта (Дневник / Мир / ...)
        self.current_section = "dnevnik"

        self.setWindowTitle(APP_NAME)

        self.resize(
            1440,
            900,
        )

        self.setMinimumSize(
            1100,
            700,
        )

        self.setup_style()
        self.setup_ui()

        self.canvas.scene.selectionChanged.connect(
            self.remember_selected_item
        )

        QApplication.instance().installEventFilter(
            self
        )

    # =====================================================
    # STYLE
    # =====================================================

    def setup_style(self):

        self.setStyleSheet(QSS)

    # =====================================================
    # UI
    # =====================================================

    def setup_ui(self):

        central = QWidget()

        self.setCentralWidget(
            central
        )

        main_layout = QHBoxLayout(
            central
        )

        main_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        main_layout.setSpacing(
            0
        )

        self.sidebar = build_sidebar(
            self
        )

        # =================================================
        # RIGHT SIDE
        # =================================================

        self.right_widget = QWidget()

        right_layout = QVBoxLayout(
            self.right_widget
        )

        right_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        right_layout.setSpacing(
            0
        )

        # =================================================
        # FORMAT TOOLBAR
        # =================================================

        self.format_toolbar = FormatToolbar(
            self
        )

        self.format_toolbar.hide()

        self.format_toolbar.format_bold.connect(
            self.apply_format_bold
        )

        self.format_toolbar.format_italic.connect(
            self.apply_format_italic
        )

        self.format_toolbar.format_underline.connect(
            self.apply_format_underline
        )

        self.format_toolbar.format_family.connect(
            self.apply_format_family
        )

        self.format_toolbar.format_size.connect(
            self.apply_format_size
        )

        self.format_toolbar.format_color.connect(
            self.apply_format_color
        )

        self.format_toolbar.format_background.connect(
            self.apply_format_background
        )

        self.format_toolbar.format_align.connect(
            self.apply_format_align
        )

        # =================================================
        # CANVAS
        # =================================================

        self.canvas = Canvas(
            self
        )

        self.arrow_follow_manager = ArrowFollowManager(
            self.canvas.scene,
            self,
        )

        self.format_toolbar_controller = (
            FormatToolbarController(
                self
            )
        )

        right_layout.addWidget(
            self.canvas
        )

        # =================================================
        # TOP NAVIGATION PANEL
        # =================================================

        self.top_navigation_panel = TopNavigationPanel(
            self,
            self,
        )

        self.top_navigation_panel.adjustSize()

        self.top_navigation_panel.show()

        if hasattr(
            self.top_navigation_panel,
            "zoom_label",
        ):

            self.zoom_label = (
                self.top_navigation_panel.zoom_label
            )

        self._center_top_navigation_panel()

        self.top_navigation_panel.raise_()

        # =================================================
        # STATUS
        # =================================================

        self.status_label = QLabel(
            "Готово"
        )

        self.status_label.setObjectName(
            "statusLabel"
        )

        self.statusBar().addWidget(
            self.status_label
        )

        main_layout.addWidget(
            self.sidebar
        )

        main_layout.addWidget(
            self.right_widget
        )

    # =====================================================
    # TOP NAVIGATION PANEL POSITION
    # =====================================================

    def _center_top_navigation_panel(self):

        if not hasattr(
            self,
            "top_navigation_panel",
        ):

            return

        panel = self.top_navigation_panel

        x = (
            self.width()
            - panel.width()
        ) // 2

        y = 14

        panel.move(
            x,
            y,
        )

        panel.raise_()

    def resizeEvent(
        self,
        event,
    ):

        super().resizeEvent(
            event
        )

        self._center_top_navigation_panel()

    # =====================================================
    # TOOLBAR BUTTON
    # =====================================================

    def toolbar_button(
        self,
        text,
        tooltip,
        callback,
    ):

        button = QToolButton()

        button.setText(
            text
        )

        button.setToolTip(
            tooltip
        )

        button.clicked.connect(
            callback
        )

        return button

    # =====================================================
    # SELECTION
    # =====================================================

    def remember_selected_item(self):

        selected = (
            self.canvas.scene.selectedItems()
        )

        if selected:

            self.last_selected_item = (
                selected[0]
            )

    # =====================================================
    # GRID
    # =====================================================

    def set_grid_mode(
        self,
        mode,
    ):

        self.canvas.grid_mode = mode

        self.canvas.viewport().update()

        self.canvas.save_board()

        self.update_status(
            "Настройка сетки изменена"
        )

    # =====================================================
    # ZOOM
    # =====================================================

    def zoom_in(self):

        self.canvas.zoom_in()

    def zoom_out(self):

        self.canvas.zoom_out()

    def update_zoom_label(
        self,
        value,
    ):

        if hasattr(
            self,
            "zoom_label",
        ):

            self.zoom_label.setText(
                f"{value}%"
            )

    # =====================================================
    # STATUS
    # =====================================================

    def update_status(
        self,
        text,
    ):

        self.status_label.setText(
            text
        )

    # =====================================================
    # PROJECT
    # =====================================================

    def new_project(self):

        name, ok = QInputDialog.getText(
            self,
            "Новый проект",
            "Название проекта:",
        )

        if not ok:

            return

        name = safe_project_name(
            name
        )

        if not name:

            return

        self.project_name = name

        # Новый проект — всегда открываем Дневник
        self.current_section = "dnevnik"

        ensure_project_folder(
            name
        )

        self.project_name_label.setText(
            name
        )

        self.canvas.scene.clear()

        self.last_selected_item = None

        self.canvas.grid_mode = "dots"

        self.canvas.set_zoom(
            100
        )

        self.update_status(
            "Создан новый проект"
        )

        self.canvas.save_board()

    def open_project(self):

        if not os.path.exists(
            BOARDS_DIR
        ):

            os.makedirs(
                BOARDS_DIR
            )

        folder = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку проекта",
            BOARDS_DIR,
        )

        if not folder:

            return

        project_name = os.path.basename(
            os.path.normpath(
                folder
            )
        )

        self.project_name = project_name

        # Открытый проект — всегда начинаем с Дневника
        self.current_section = "dnevnik"

        self.project_name_label.setText(
            project_name
        )

        self.last_selected_item = None

        self.canvas.load_board(
            project_name
        )

    def save_project(self):

        if not self.project_name:

            self.new_project()

            return

        self.canvas.save_board()

        self.update_status(
            "Проект сохранен"
        )

    # =====================================================
    # ADD NORMAL CARD
    # =====================================================

    def add_card(
        self,
        card_type="text",
    ):

        if not self.project_name:

            QMessageBox.information(
                self,
                "Проект не выбран",
                "Сначала создайте или откройте проект.",
            )

            return

        card_titles = {
            "text": "Новая карточка",
            "comment": "Комментарий",
            "heading": "Заголовок",
            "image_text": "Текст + изображение",
            "color": "Цвет",
        }

        title = card_titles.get(
            card_type,
            "Новая карточка",
        )

        card = self.canvas.add_card(
            title="",
            card_type=card_type,
        )

        if card is None:

            return

        card.setSelected(
            True
        )

        self.last_selected_item = card

        self.update_status(
            "Добавлена карточка: "
            + title
        )

        self.canvas.save_board()

    # =====================================================
    # ADD COLOR CARD
    # =====================================================

    def add_color_card(self):

        if not self.project_name:

            QMessageBox.information(
                self,
                "Проект не выбран",
                "Сначала создайте или откройте проект.",
            )

            return

        card = self.canvas.add_card(
            title="Цвет",
            card_type="color",
        )

        if card is None:

            return

        card.setSelected(
            True
        )

        self.last_selected_item = card

        self.update_status(
            "Добавлена цветовая ячейка"
        )

        self.canvas.save_board()

    # =====================================================
    # CHANGE SELECTED COLOR
    # =====================================================

    def change_selected_color(self):

        item = None

        selected = (
            self.canvas.scene.selectedItems()
        )

        if selected:

            item = selected[0]

        elif self.last_selected_item is not None:

            item = self.last_selected_item

        if item is None:

            self.update_status(
                "Сначала выберите элемент"
            )

            return

        _show_color_palette(
            self.canvas,
            item,
        )

    # =====================================================
    # IMAGE + TEXT
    # =====================================================

    def add_image_text_card(self):

        if not self.project_name:

            QMessageBox.information(
                self,
                "Проект не выбран",
                "Сначала создайте или откройте проект.",
            )

            return

        self.canvas.add_image_text_card()

    # =====================================================
    # VIDEO + TEXT
    # =====================================================

    def add_video_text_card(self):

        if not self.project_name:

            QMessageBox.information(
                self,
                "Проект не выбран",
                "Сначала создайте или откройте проект.",
            )

            return

        self.canvas.add_video_text_card()

    # =====================================================
    # IMAGE
    # =====================================================

    def add_image(self):

        if not self.project_name:

            QMessageBox.information(
                self,
                "Проект не выбран",
                "Сначала создайте или откройте проект.",
            )

            return

        self.canvas.add_image()

    # =====================================================
    # FILE
    # =====================================================

    def add_file(self):

        if not self.project_name:

            QMessageBox.information(
                self,
                "Проект не выбран",
                "Сначала создайте или откройте проект.",
            )

            return

        self.canvas.add_file()

    # =====================================================
    # DELETE
    # =====================================================

    def delete_selected(self):

        selected = (
            self.canvas.scene.selectedItems()
        )

        if selected:

            self.canvas.delete_selected()

            self.last_selected_item = None

            return

        item = self.last_selected_item

        if item is None:

            return

        if item.scene() is None:

            self.last_selected_item = None

            return

        item.setSelected(
            True
        )

        self.canvas.delete_selected()

        self.last_selected_item = None

    # =====================================================
    # SETTINGS
    # =====================================================

    def open_settings(self):

        dialog = SettingsDialog(
            self.canvas,
            self,
        )

        if dialog.exec():

            self.canvas.save_board()

            self.update_status(
                "Настройки сохранены"
            )

    # =====================================================
    # DIALOGUE EDITOR
    # =====================================================

    def open_dialogue_editor(self):

        if not self.project_name:
            QMessageBox.information(
                self,
                "Диалоги",
                "Сначала создайте или откройте проект.",
            )
            return

        from .dialogue import DialogueEditorWindow
        from .utils import ensure_project_folder

        project_folder = ensure_project_folder(
            self.project_name
        )

        if getattr(self, "_dialogue_editor", None) is None:
            self._dialogue_editor = DialogueEditorWindow(
                project_folder,
                parent=self,
            )

        self._dialogue_editor.show()
        self._dialogue_editor.raise_()
        self._dialogue_editor.activateWindow()

    # =====================================================
    # FORMAT TOOLBAR — ACTIVATION
    # =====================================================

    def activate_text(
        self,
        text_item,
    ):
        """
        Вызывается, когда EditableText включает редактирование.
        Показывает плавающий тулбар рядом с активным текстом.
        """

        self.active_text_item = text_item

        if hasattr(
            self,
            "canvas",
        ):

            self.canvas.setDragMode(
                self.canvas.DragMode.NoDrag
            )

        if hasattr(
            self,
            "format_toolbar_controller",
        ):

            self.format_toolbar_controller.show_for_item(
                text_item
            )

    def deactivate_text(self):
        """
        Вызывается, когда EditableText выключает редактирование.
        Скрывает плавающий тулбар.
        """

        self.active_text_item = None

        if hasattr(
            self,
            "canvas",
        ):

            self.canvas.setDragMode(
                self.canvas.DragMode.RubberBandDrag
            )

        if hasattr(
            self,
            "format_toolbar_controller",
        ):

            self.format_toolbar_controller.hide()

    # =====================================================
    # FORMAT TOOLBAR — APPLY
    # =====================================================

    def apply_format_bold(
        self,
        checked,
    ):

        if self.active_text_item is None:

            return

        self.format_toolbar.toggle_bold(
            self.active_text_item,
            checked,
        )

    def apply_format_italic(
        self,
        checked,
    ):

        if self.active_text_item is None:

            return

        self.format_toolbar.toggle_italic(
            self.active_text_item,
            checked,
        )

    def apply_format_underline(
        self,
        checked,
    ):

        if self.active_text_item is None:

            return

        self.format_toolbar.toggle_underline(
            self.active_text_item,
            checked,
        )

    def apply_format_family(
        self,
        family,
    ):

        if self.active_text_item is None:

            return

        self.format_toolbar.apply_family(
            self.active_text_item,
            family,
        )

    def apply_format_size(
        self,
        size,
    ):

        if self.active_text_item is None:

            return

        self.format_toolbar.apply_size(
            self.active_text_item,
            size,
        )

    def apply_format_color(
        self,
        color,
    ):

        if self.active_text_item is None:

            return

        self.format_toolbar.apply_color(
            self.active_text_item,
            color,
        )

    def apply_format_background(
        self,
        color,
    ):

        if self.active_text_item is None:

            return

        self.format_toolbar.apply_background(
            self.active_text_item,
            color,
        )

    def apply_format_align(
        self,
        alignment,
    ):

        if self.active_text_item is None:

            return

        self.format_toolbar.apply_align(
            self.active_text_item,
            alignment,
        )

    # =====================================================
    # EVENT FILTER
    # =====================================================

    def eventFilter(
        self,
        watched,
        event,
    ):

        # =====================================================
        # DELETE
        # =====================================================

        if (
            event.type()
            == event.Type.KeyPress
            and
            event.key()
            == Qt.Key.Key_Delete
        ):

            focus_item = (
                self.canvas.scene.focusItem()
            )

            if isinstance(
                focus_item,
                QGraphicsTextItem,
            ):

                return False

            self.delete_selected()

            return True

        # =====================================================
        # CTRL+C / CTRL+V / CTRL+A
        # =====================================================
        # Перехватываем ДО EditableText, чтобы QGraphicsTextItem
        # не поглотил эти события. Логика внутри handler-ов
        # сама решает: текст или карточки.

        if event.type() == event.Type.KeyPress:

            mods = event.modifiers()

            if mods & Qt.KeyboardModifier.ControlModifier:

                key = event.key()

                # Если фокус в тексте — НЕ перехватываем.
                try:
                    focus_item = self.canvas.scene.focusItem()

                    if focus_item is not None:
                        type_name = type(focus_item).__name__

                        if type_name in (
                            "EditableText",
                            "CardTextItem",
                            "QGraphicsTextItem",
                        ):
                            return False
                except Exception:
                    pass

                if getattr(self, "active_text_item", None) is not None:
                    return False

                # Иначе — карточки.
                if key == Qt.Key.Key_C:

                    self._handle_ctrl_c()
                    return True

                if key == Qt.Key.Key_V:

                    self._handle_ctrl_v()
                    return True

                if key == Qt.Key.Key_A:

                    self._handle_ctrl_a()
                    return True

        return super().eventFilter(
            watched,
            event,
        )

    # =====================================================
    # KEYBOARD SHORTCUTS
    # =====================================================

    def keyPressEvent(
        self,
        event,
    ):

        modifiers = event.modifiers()

        if (
            modifiers
            &
            Qt.KeyboardModifier.ControlModifier
        ):

            if event.key() == Qt.Key.Key_S:

                self.save_project()

                event.accept()

                return

            if event.key() == Qt.Key.Key_O:

                self.open_project()

                event.accept()

                return

            if event.key() == Qt.Key.Key_N:

                self.new_project()

                event.accept()

                return

            # =================================================
            # COPY / PASTE / SELECT ALL
            # =================================================
            # Если фокус в текстовом поле — Qt сам обработает
            # Ctrl+C/V/A. Пропускаем.
            # Иначе — копируем/вставляем/выделяем карточки.

            # =================================================
            # Ctrl+C — копируем карточки, если они выделены.
            # =================================================

            if event.key() == Qt.Key.Key_C:

                if self._has_selected_cards():

                    self._copy_selected_cards()

                    event.accept()
                    return

            # =================================================
            # Ctrl+V — вставляем карточки, если буфер не пуст.
            # =================================================

            if event.key() == Qt.Key.Key_V:

                if getattr(self, "_clipboard_cards", None):

                    self._paste_cards()

                    event.accept()
                    return

            # =================================================
            # Ctrl+A — выделяем карточки, если не редактируем текст.
            # =================================================

            if event.key() == Qt.Key.Key_A:

                if not self._is_text_focused():

                    self._select_all_cards()

                    event.accept()
                    return

                if event.key() == Qt.Key.Key_V:

                    self._paste_cards()

                    event.accept()
                    return

                if event.key() == Qt.Key.Key_A:

                    self._select_all_cards()

                    event.accept()
                    return

        super().keyPressEvent(
            event
        )

    # =====================================================
    # COPY / PASTE / SELECT ALL
    # =====================================================

    def _is_text_focused(self):
        """True, если текст в режиме редактирования (тулбар активен)."""

        return getattr(self, "active_text_item", None) is not None

    def _has_selected_cards(self):
        """True, если есть хотя бы одна выделенная карточка."""

        try:
            scene = self.canvas.scene

            if scene is None:
                print(f"[COPY-DEBUG] _has_selected_cards: scene=None")
                return False

            from .window_clipboard import is_internal

            sel = scene.selectedItems()

            for item in sel:

                if is_internal(item):
                    continue

                return True

            return False

        except Exception as exc:
            print(f"[COPY-DEBUG] _has_selected_cards error: {exc!r}")
            return False

    def _copy_selected_cards(self):
        """Сериализует выделенные карточки в self._clipboard_cards."""

        from .window_clipboard import serialize_item

        selected = self.canvas.scene.selectedItems()

        self._clipboard_cards = []

        for item in selected:
            data = serialize_item(item)

            if data:
                self._clipboard_cards.append(data)

        if self._clipboard_cards:
            self.update_status(
                f"Скопировано: {len(self._clipboard_cards)}"
            )

    def _paste_cards(self):
        """Создаёт новые карточки из self._clipboard_cards."""

        from .window_clipboard import paste_cards_into_canvas

        if not getattr(self, "_clipboard_cards", None):
            return

        new_items = paste_cards_into_canvas(
            self.canvas,
            self._clipboard_cards,
        )

        if new_items:

            self.canvas.scene.clearSelection()

            for item in new_items:

                try:
                    item.setSelected(True)
                except Exception:
                    pass

            self.update_status(
                f"Вставлено: {len(new_items)}"
            )

    def _select_all_cards(self):
        """Выделяет все карточки на сцене."""

        from .window_clipboard import get_selectable_items

        scene = self.canvas.scene

        if scene is None:
            return

        scene.clearSelection()

        count = 0

        for item in get_selectable_items(scene):

            try:
                item.setSelected(True)
                count += 1
            except Exception:
                pass

        if count:
            self.update_status(
                f"Выделено: {count}"
            )

    # =====================================================
    # GLOBAL HOTKEY HANDLERS
    # =====================================================

    def _handle_ctrl_c(self):
        """Ctrl+C: копируем текст (если в фокусе) или карточки."""

        # Приоритет — выделенные карточки.
        if self._has_selected_cards():
            self._copy_selected_cards()
            return

        # Иначе — текст в фокусе.
        if self._is_text_focused():

            item = self.active_text_item

            if item is not None:
                try:
                    item.copy()
                except Exception:
                    pass

    def _handle_ctrl_v(self):
        """Ctrl+V: вставляем текст (если в фокусе) или карточки."""

        # Приоритет — буфер карточек.
        if getattr(self, "_clipboard_cards", None):
            self._paste_cards()
            return

        # Иначе — текст в фокусе.
        if self._is_text_focused():

            item = self.active_text_item

            if item is not None:
                try:
                    item.paste()
                except Exception:
                    pass

    def _handle_ctrl_a(self):
        """Ctrl+A: выделяем текст (если в фокусе) или карточки."""

        if self._is_text_focused():

            item = self.active_text_item

            if item is not None:
                try:
                    from PySide6.QtGui import QTextCursor

                    cursor = item.textCursor()
                    cursor.select(QTextCursor.SelectionType.Document)
                    item.setTextCursor(cursor)
                except Exception:
                    pass

            return

        self._select_all_cards()

    # =====================================================
    # SECTION SWITCHING
    # =====================================================

    def switch_section(self, slug):
        """Переключает активный раздел проекта."""

        if slug == getattr(self, "current_section", None):
            return

        if not self.project_name:
            return

        # Сохранить текущий раздел
        try:
            self.canvas.save_board()
        except Exception as exc:
            print(f"[SECTION] save failed: {exc!r}")

        # Переключить
        self.current_section = slug

        # Загрузить новый раздел
        try:
            self.canvas.load_board(self.project_name)
        except Exception as exc:
            print(f"[SECTION] load failed: {exc!r}")

        # Обновить выделение кнопок
        try:
            self.update_section_buttons()
        except Exception:
            pass

        # Обновить статус
        try:
            from .config import SECTION_LABELS

            label = SECTION_LABELS.get(slug, slug)

            self.update_status(f"Раздел: {label}")
        except Exception:
            pass

    def update_section_buttons(self):
        """Подсвечивает активную кнопку раздела."""

        from .config import SECTIONS

        buttons = getattr(self, "section_buttons", None)

        if not buttons:
            return

        for index, (slug, _label) in enumerate(SECTIONS):

            if index >= len(buttons):
                break

            button = buttons[index]

            try:
                if slug == self.current_section:
                    button.setObjectName("activeSection")
                else:
                    button.setObjectName("")
            except Exception:
                pass

            # Qt требует перерисовку после смены objectName
            try:
                button.style().unpolish(button)
                button.style().polish(button)
            except Exception:
                pass

    # =====================================================
    # CLOSE
    # =====================================================

    def closeEvent(
        self,
        event,
    ):

        if self.project_name:

            self.canvas.save_board()

        if hasattr(
            self,
            "arrow_follow_manager",
        ):

            self.arrow_follow_manager.stop()

        QApplication.instance().removeEventFilter(
            self
        )

        event.accept()