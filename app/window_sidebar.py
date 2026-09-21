"""Sidebar builder for DevJournal."""

from PySide6.QtCore import (
    Qt,
    QEvent,
    QPropertyAnimation,
    QEasingCurve,
)
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QLabel,
    QPushButton,
)


class SidebarHandle(QFrame):

    def __init__(
        self,
        window,
        controller,
    ):
        super().__init__(window)

        self.controller = controller

        self.setObjectName(
            "sidebarHandle"
        )

        self.setFixedSize(
            28,
            70,
        )

        self.setStyleSheet(
            """
            QFrame#sidebarHandle {
                background: #FFFFFF;
                border: 1px solid #DCDCD7;
                border-radius: 14px;
            }

            QFrame#sidebarHandle:hover {
                background: #F2F2EF;
            }
            """
        )

        self.setMouseTracking(
            True
        )

        self.raise_()

    def enterEvent(
        self,
        event,
    ):
        self.controller.show_sidebar()

        super().enterEvent(
            event
        )

    def leaveEvent(
        self,
        event,
    ):
        self.controller._check_mouse_position()

        super().leaveEvent(
            event
        )


class SidebarHoverController(QFrame):

    def __init__(
        self,
        window,
        sidebar,
    ):
        super().__init__(window)

        self.window = window
        self.sidebar = sidebar
        self.handle = None

        self.setObjectName(
            "sidebarHoverZone"
        )

        self.setFixedWidth(
            8
        )

        self.setAttribute(
            Qt.WA_TransparentForMouseEvents,
            False,
        )

        self.setMouseTracking(
            True
        )

        self.animation = QPropertyAnimation(
            self.sidebar,
            b"maximumWidth",
            self,
        )

        self.animation.setDuration(
            180
        )

        self.animation.setEasingCurve(
            QEasingCurve.OutCubic
        )

        self.sidebar.installEventFilter(
            self
        )

        self.window.installEventFilter(
            self
        )

        self._expanded = False
        self._pinned = False

        self.move(
            0,
            0,
        )

        self.raise_()

    def set_handle(
        self,
        handle,
    ):
        self.handle = handle

        self._position_handle()

        self.handle.raise_()

    def toggle_pin(self) -> None:
        """Переключить закрепление панели."""
        self._pinned = not self._pinned
        if self._pinned:
            self.show_sidebar()
        else:
            self._check_mouse_position()

    def _position_handle(
        self,
    ):
        if self.handle is None:
            return

        handle_x = 0

        handle_y = (
            self.window.height()
            - self.handle.height()
        ) // 2

        self.handle.move(
            handle_x,
            handle_y,
        )

        if not self._expanded and not self._pinned:
            self.handle.show()
            self.handle.raise_()

    def show_sidebar(
        self,
    ):
        if self._expanded:
            return

        self._expanded = True

        if self.handle is not None:
            self.handle.hide()

        self.animation.stop()

        self.animation.setStartValue(
            self.sidebar.width()
        )

        self.animation.setEndValue(
            235
        )

        self.animation.start()

        self.sidebar.raise_()

    def hide_sidebar(
        self,
    ):
        if self._pinned:
            return

        if not self._expanded:
            return

        self._expanded = False

        self.animation.stop()

        self.animation.setStartValue(
            self.sidebar.width()
        )

        self.animation.setEndValue(
            0
        )

        self.animation.start()

        if self.handle is not None:
            self.handle.show()
            self.handle.raise_()

    def enterEvent(
        self,
        event,
    ):
        self.show_sidebar()

        super().enterEvent(
            event
        )

    def leaveEvent(
        self,
        event,
    ):
        self._check_mouse_position()

        super().leaveEvent(
            event
        )

    def eventFilter(
        self,
        watched,
        event,
    ):
        if event.type() == QEvent.MouseMove:
            self._check_mouse_position()

        elif event.type() == QEvent.Leave:
            self._check_mouse_position()

        elif event.type() == QEvent.Resize:

            if watched is self.window:

                self.setGeometry(
                    0,
                    0,
                    8,
                    self.window.height(),
                )

                self.sidebar.setFixedHeight(
                    self.window.height()
                )

                self._position_handle()

        return super().eventFilter(
            watched,
            event
        )

    def _check_mouse_position(
        self,
    ):
        if self._pinned:
            self.show_sidebar()
            return

        cursor_pos = self.window.mapFromGlobal(
            self.window.cursor().pos()
        )

        sidebar_rect = self.sidebar.geometry()

        hover_zone = self.geometry()

        handle_rect = (
            self.handle.geometry()
            if self.handle is not None
            else None
        )

        if (
            hover_zone.contains(
                cursor_pos
            )
            or sidebar_rect.contains(
                cursor_pos
            )
            or (
                handle_rect is not None
                and handle_rect.contains(
                    cursor_pos
                )
            )
        ):
            self.show_sidebar()
            return

        self.hide_sidebar()


def build_sidebar(
    window,
):

    # =================================================
    # SIDEBAR
    # =================================================

    window.sidebar = QFrame(
        window
    )

    window.sidebar.setObjectName(
        "sidebar"
    )

    window.sidebar.setMinimumWidth(
        0
    )

    window.sidebar.setMaximumWidth(
        0
    )

    window.sidebar.setFixedHeight(
        window.height()
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

    # Кнопка «Закрепить»
    window.pin_button = QPushButton("📌 Закрепить")
    window.pin_button.setCursor(
        Qt.CursorShape.PointingHandCursor
    )
    window.pin_button.setCheckable(True)
    window.pin_button.setStyleSheet(
        """
        QPushButton {
            text-align: left;
            padding: 6px 10px;
            border: 1px solid #DCDCD7;
            border-radius: 4px;
            background: #FFFFFF;
            color: #333;
            font-size: 11px;
        }
        QPushButton:hover {
            background: #F2F2EF;
        }
        QPushButton:checked {
            background: #E8F0FE;
            color: #0055CC;
            border-color: #0055CC;
        }
        """
    )

    def _toggle_pin(checked=False):
        ctrl = getattr(window, "sidebar_hover_controller", None)
        if ctrl is not None:
            ctrl.toggle_pin()
            window.pin_button.setText(
                "📌 Закреплено" if ctrl._pinned else "📌 Закрепить"
            )

    window.pin_button.clicked.connect(_toggle_pin)

    sidebar_layout.addWidget(
        window.pin_button
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

    from .config import SECTIONS

    window.section_buttons = []

    for index, (slug, label) in enumerate(SECTIONS):

        button = QPushButton(
            label
        )

        button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        if index == 0:

            button.setObjectName(
                "activeSection"
            )

        button.clicked.connect(
            lambda checked=False, s=slug: window.switch_section(s)
        )

        sidebar_layout.addWidget(
            button
        )

        window.section_buttons.append(
            button
        )

    sidebar_layout.addStretch()

    # =================================================
    # HOVER ZONE
    # =================================================

    window.sidebar_hover_controller = (
        SidebarHoverController(
            window,
            window.sidebar,
        )
    )

    window.sidebar_hover_controller.setGeometry(
        0,
        0,
        8,
        window.height(),
    )

    # =================================================
    # SIDEBAR HANDLE
    # =================================================

    window.sidebar_handle = SidebarHandle(
        window,
        window.sidebar_hover_controller,
    )

    window.sidebar_hover_controller.set_handle(
        window.sidebar_handle
    )

    # =================================================
    # SHOW
    # =================================================

    window.sidebar.show()

    window.sidebar.raise_()

    window.sidebar_hover_controller.raise_()

    window.sidebar_handle.show()
    window.sidebar_handle.raise_()

    return window.sidebar