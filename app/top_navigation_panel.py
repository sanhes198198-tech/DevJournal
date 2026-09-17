from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QToolButton,
    QMenu,
    QLabel,
)

from .project_delete import delete_project_dialog
from .canvas.frame_item import add_frame
from .window_actions import unlock_all_frames, unlock_frame_under_cursor


class TopNavigationPanel(QFrame):

    def __init__(self, window, parent=None):
        super().__init__(parent)

        self.window = window

        self.setObjectName(
            "topNavigationPanel"
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_StyledBackground,
            True,
        )

        self.setMinimumHeight(
            42
        )

        self.setStyleSheet(
            """
            QFrame#topNavigationPanel {
                background: #FFFFFF;
                border: 1px solid #DCDCD7;
                border-radius: 16px;
            }
            """
        )

        self._build_ui()

    def _build_ui(self):

        layout = QHBoxLayout(
            self
        )

        layout.setContentsMargins(
            8,
            5,
            8,
            5,
        )

        layout.setSpacing(
            3
        )

        # PROJECT

        project_button = self._create_menu_button(
            "Проект"
        )

        project_button.setMinimumWidth(
            68
        )

        project_menu = QMenu(
            project_button
        )

        new_action = project_menu.addAction(
            "Создать проект"
        )

        open_action = project_menu.addAction(
            "Открыть проект"
        )

        project_menu.addSeparator()

        save_action = project_menu.addAction(
            "Сохранить"
        )

        project_menu.addSeparator()

        delete_action = project_menu.addAction(
            "Удалить проект…"
        )

        new_action.triggered.connect(
            self.window.new_project
        )

        open_action.triggered.connect(
            self.window.open_project
        )

        save_action.triggered.connect(
            self.window.save_project
        )

        delete_action.triggered.connect(
            lambda: delete_project_dialog(
                self.window
            )
        )

        project_button.setMenu(
            project_menu
        )

        layout.addWidget(
            project_button
        )

        # EDIT

        edit_button = self._create_menu_button(
            "Правка"
        )

        edit_button.setMinimumWidth(
            64
        )

        edit_menu = QMenu(
            edit_button
        )

        settings_action = edit_menu.addAction(
            "Настройки"
        )

        edit_menu.addSeparator()

        grid_dots_action = edit_menu.addAction(
            "Сетка: точки"
        )

        grid_lines_action = edit_menu.addAction(
            "Сетка: линии"
        )

        grid_none_action = edit_menu.addAction(
            "Сетка: выключена"
        )

        settings_action.triggered.connect(
            self.window.open_settings
        )

        grid_dots_action.triggered.connect(
            lambda: self.window.set_grid_mode(
                "dots"
            )
        )

        grid_lines_action.triggered.connect(
            lambda: self.window.set_grid_mode(
                "grid"
            )
        )

        grid_none_action.triggered.connect(
            lambda: self.window.set_grid_mode(
                "none"
            )
        )

        edit_button.setMenu(
            edit_menu
        )

        layout.addWidget(
            edit_button
        )

        # CARDS

        cards_button = self._create_menu_button(
            "Карточки"
        )

        cards_button.setMinimumWidth(
            76
        )

        cards_menu = QMenu(
            cards_button
        )

        text_action = cards_menu.addAction(
            "Обычная"
        )

        comment_action = cards_menu.addAction(
            "Комментарий"
        )

        heading_action = cards_menu.addAction(
            "Заголовок + текст"
        )

        image_text_action = cards_menu.addAction(
            "Текст + изображение"
        )

        video_text_action = cards_menu.addAction(
            "Текст + видео"
        )

        color_action = cards_menu.addAction(
            "Цвет"
        )

        cards_menu.addSeparator()

        frame_action = cards_menu.addAction(
            "Рамка"
        )

        cards_menu.addSeparator()

        unlock_frames_action = cards_menu.addAction(
            "Разблокировать все рамки"
        )

        unlock_under_cursor_action = cards_menu.addAction(
            "Разблокировать рамку под курсором"
        )

        text_action.triggered.connect(
            lambda: self.window.add_card(
                "text"
            )
        )

        comment_action.triggered.connect(
            lambda: self.window.add_card(
                "comment"
            )
        )

        heading_action.triggered.connect(
            lambda: self.window.add_card(
                "heading"
            )
        )

        image_text_action.triggered.connect(
            self.window.add_image_text_card
        )

        video_text_action.triggered.connect(
            self.window.add_video_text_card
        )

        color_action.triggered.connect(
            self.window.add_color_card
        )

        frame_action.triggered.connect(
            lambda: add_frame(
                self.window.canvas
            )
        )

        unlock_frames_action.triggered.connect(
            lambda: unlock_all_frames(
                self.window
            )
        )

        unlock_under_cursor_action.triggered.connect(
            lambda: unlock_frame_under_cursor(
                self.window
            )
        )

        cards_button.setMenu(
            cards_menu
        )

        layout.addWidget(
            cards_button
        )

        # IMAGE

        image_button = self._create_button(
            "Изображение",
            "Добавить изображение",
            self.window.add_image,
        )

        image_button.setMinimumWidth(
            100
        )

        layout.addWidget(
            image_button
        )

        # FILE

        file_button = self._create_button(
            "Файл",
            "Добавить файл",
            self.window.add_file,
        )

        file_button.setMinimumWidth(
            54
        )

        layout.addWidget(
            file_button
        )

        # ZOOM

        zoom_minus = self._create_button(
            "−",
            "Уменьшить масштаб",
            self.window.zoom_out,
        )

        zoom_minus.setMinimumWidth(
            28
        )

        layout.addWidget(
            zoom_minus
        )

        self.zoom_label = QLabel(
            "100%"
        )

        self.zoom_label.setObjectName(
            "topNavigationZoomLabel"
        )

        self.zoom_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.zoom_label.setMinimumWidth(
            44
        )

        layout.addWidget(
            self.zoom_label
        )

        zoom_plus = self._create_button(
            "+",
            "Увеличить масштаб",
            self.window.zoom_in,
        )

        zoom_plus.setMinimumWidth(
            28
        )

        layout.addWidget(
            zoom_plus
        )

        self.adjustSize()

    def _create_button(
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

        button.setObjectName(
            "topNavigationButton"
        )

        button.setSizePolicy(
            button.sizePolicy().Policy.Preferred,
            button.sizePolicy().Policy.Fixed,
        )

        button.clicked.connect(
            callback
        )

        return button

    def _create_menu_button(
        self,
        text,
    ):

        button = QToolButton()

        button.setText(
            text
        )

        button.setObjectName(
            "topNavigationMenuButton"
        )

        button.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )

        button.setStyleSheet(
            """
            QToolButton#topNavigationMenuButton {
                padding-right: 10px;
            }

            QToolButton#topNavigationMenuButton::menu-indicator {
                image: none;
                width: 0px;
                height: 0px;
            }
            """
        )

        button.setSizePolicy(
            button.sizePolicy().Policy.Preferred,
            button.sizePolicy().Policy.Fixed,
        )

        return button