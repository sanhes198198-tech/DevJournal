"""Toolbar builder for DevJournal."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QToolButton,
    QMenu,
    QLabel,
)


def build_toolbar(window):

    # =================================================
    # TOOLBAR
    # =================================================

    toolbar = QFrame()

    toolbar.setObjectName(
        "toolbar"
    )

    toolbar_layout = QHBoxLayout(
        toolbar
    )

    toolbar_layout.setContentsMargins(
        12,
        4,
        12,
        4,
    )

    toolbar_layout.setSpacing(
        4
    )

    # =================================================
    # FILE MENU
    # =================================================

    file_button = QToolButton()

    file_button.setText(
        "File"
    )

    file_button.setObjectName(
        "menuButton"
    )

    file_button.setPopupMode(
        QToolButton.ToolButtonPopupMode.InstantPopup
    )

    file_menu = QMenu(
        file_button
    )

    new_action = file_menu.addAction(
        "Создать проект"
    )

    open_action = file_menu.addAction(
        "Открыть проект"
    )

    file_menu.addSeparator()

    save_action = file_menu.addAction(
        "Сохранить"
    )

    new_action.triggered.connect(
        window.new_project
    )

    open_action.triggered.connect(
        window.open_project
    )

    save_action.triggered.connect(
        window.save_project
    )

    file_button.setMenu(
        file_menu
    )

    toolbar_layout.addWidget(
        file_button
    )

    # =================================================
    # EDIT MENU
    # =================================================

    edit_button = QToolButton()

    edit_button.setText(
        "Edit"
    )

    edit_button.setObjectName(
        "menuButton"
    )

    edit_button.setPopupMode(
        QToolButton.ToolButtonPopupMode.InstantPopup
    )

    edit_menu = QMenu(
        edit_button
    )

    settings_action = edit_menu.addAction(
        "Настройки рабочего пространства"
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
        window.open_settings
    )

    grid_dots_action.triggered.connect(
        lambda: window.set_grid_mode(
            "dots"
        )
    )

    grid_lines_action.triggered.connect(
        lambda: window.set_grid_mode(
            "grid"
        )
    )

    grid_none_action.triggered.connect(
        lambda: window.set_grid_mode(
            "none"
        )
    )

    edit_button.setMenu(
        edit_menu
    )

    toolbar_layout.addWidget(
        edit_button
    )

    toolbar_layout.addSpacing(
        12
    )

    # =================================================
    # ADD CARD MENU
    # =================================================

    add_text_button = QToolButton()

    add_text_button.setText(
        "+ Текст"
    )

    add_text_button.setToolTip(
        "Добавить карточку"
    )

    add_text_button.setPopupMode(
        QToolButton.ToolButtonPopupMode.InstantPopup
    )

    card_menu = QMenu(
        add_text_button
    )

    text_action = card_menu.addAction(
        "Обычная"
    )

    comment_action = card_menu.addAction(
        "Комментарий"
    )

    heading_action = card_menu.addAction(
        "Заголовок + текст"
    )

    image_text_action = card_menu.addAction(
        "Текст + изображение"
    )

    video_text_action = card_menu.addAction(
        "Текст + видео"
    )

    color_action = card_menu.addAction(
        "Цвет"
    )

    text_action.triggered.connect(
        lambda: window.add_card(
            "text"
        )
    )

    comment_action.triggered.connect(
        lambda: window.add_card(
            "comment"
        )
    )

    heading_action.triggered.connect(
        lambda: window.add_card(
            "heading"
        )
    )

    image_text_action.triggered.connect(
        window.add_image_text_card
    )

    video_text_action.triggered.connect(
        window.add_video_text_card
    )

    color_action.triggered.connect(
        window.add_color_card
    )

    add_text_button.setMenu(
        card_menu
    )

    toolbar_layout.addWidget(
        add_text_button
    )

    # =================================================
    # IMAGE
    # =================================================

    image_button = window.toolbar_button(
        "Image",
        "Добавить изображение",
        window.add_image,
    )

    toolbar_layout.addWidget(
        image_button
    )

    # =================================================
    # FILE
    # =================================================

    file_item_button = window.toolbar_button(
        "File",
        "Добавить файл",
        window.add_file,
    )

    toolbar_layout.addWidget(
        file_item_button
    )

    toolbar_layout.addStretch()

    # =================================================
    # ZOOM
    # =================================================

    zoom_minus = window.toolbar_button(
        "−",
        "Уменьшить масштаб",
        window.zoom_out,
    )

    toolbar_layout.addWidget(
        zoom_minus
    )

    window.zoom_label = QLabel(
        "100%"
    )

    window.zoom_label.setObjectName(
        "zoomLabel"
    )

    window.zoom_label.setAlignment(
        Qt.AlignmentFlag.AlignCenter
    )

    toolbar_layout.addWidget(
        window.zoom_label
    )

    zoom_plus = window.toolbar_button(
        "+",
        "Увеличить масштаб",
        window.zoom_in,
    )

    toolbar_layout.addWidget(
        zoom_plus
    )

    return toolbar