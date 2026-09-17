"""Sidebar builder for DevJournal."""

from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QLabel,
    QPushButton,
)


def build_sidebar(window):

    # =================================================
    # SIDEBAR
    # =================================================

    window.sidebar = QFrame()

    window.sidebar.setObjectName(
        "sidebar"
    )

    window.sidebar.setFixedWidth(
        235
    )

    sidebar_layout = QVBoxLayout(
        window.sidebar
    )

    sidebar_layout.setContentsMargins(
        16,
        18,
        16,
        16,
    )

    sidebar_layout.setSpacing(
        5
    )

    app_title = QLabel(
        "DevJournal"
    )

    app_title.setObjectName(
        "appTitle"
    )

    sidebar_layout.addWidget(
        app_title
    )

    project_label = QLabel(
        "ЛИЧНЫЙ ДНЕВНИК РАЗРАБОТЧИКА"
    )

    project_label.setObjectName(
        "projectLabel"
    )

    sidebar_layout.addWidget(
        project_label
    )

    sidebar_layout.addSpacing(
        22
    )

    project_section = QLabel(
        "PROJECT"
    )

    project_section.setObjectName(
        "sectionLabel"
    )

    sidebar_layout.addWidget(
        project_section
    )

    window.project_name_label = QLabel(
        "Проект не выбран"
    )

    window.project_name_label.setStyleSheet(
        """
        font-weight: 600;
        padding: 7px 0;
        """
    )

    sidebar_layout.addWidget(
        window.project_name_label
    )

    sidebar_layout.addSpacing(
        18
    )

    sections_label = QLabel(
        "РАЗДЕЛЫ"
    )

    sections_label.setObjectName(
        "sectionLabel"
    )

    sidebar_layout.addWidget(
        sections_label
    )

    sections = [
        "📖  Дневник",
        "🌍  Мир",
        "👤  Персонажи",
        "🏙  Локации",
        "🎮  Геймплей",
        "🎨  Арт",
        "🔧  Техника",
    ]

    window.section_buttons = []

    for index, name in enumerate(
        sections
    ):

        button = QPushButton(
            name
        )

        if index == 0:

            button.setObjectName(
                "activeSection"
            )

        sidebar_layout.addWidget(
            button
        )

        window.section_buttons.append(
            button
        )

    sidebar_layout.addStretch()

    return window.sidebar