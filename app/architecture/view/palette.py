"""
PalettePanel — левая панель архитектурных элементов.

Пресеты — dropdown по категории.
Drag-to-create — отдельная кнопка «+ Своя комната».
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QMenu,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QFrame,
)


class PalettePanel(QWidget):
    """Левая панель: палитра элементов."""

    # Для drag-to-create (свободный прямоугольник)
    element_requested = Signal(str)

    # Для создания из пресета
    preset_requested = Signal(str)

    # Для вставки Asset (векторного)
    asset_requested = Signal(str)

    WIDTH = 220

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedWidth(self.WIDTH)
        self._asset_registry = None
        self._build_ui()

    # ------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Элементы")
        title.setStyleSheet(
            "font-weight: 600; font-size: 12px; "
            "color: #E5E5E5; padding-bottom: 4px;"
        )
        layout.addWidget(title)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: #2A2D33;")
        layout.addWidget(line)

        # --- Категория: Комната ---
        self._add_category_dropdown(
            layout,
            label="Комната",
            category="rooms",
        )

        # Разделитель
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet("color: #2A2D33; margin: 4px 0;")
        layout.addWidget(sep)

        # --- Своя комната (drag-to-create) ---
        self._add_custom_button(
            layout,
            label="+ Своя комната",
            tooltip="Нарисуйте прямоугольник на canvas",
            type_name="room",
        )

        # Разделитель
        sep_asset = QFrame()
        sep_asset.setFrameShape(QFrame.Shape.HLine)
        sep_asset.setFrameShadow(QFrame.Shadow.Sunken)
        sep_asset.setStyleSheet("color: #2A2D33; margin: 4px 0;")
        layout.addWidget(sep_asset)

        # --- Векторные ассеты ---
        self._add_asset_dropdown(layout, label="Ассет")

        layout.addStretch()

        hint = QLabel(
            "Ассеты создаются в векторном редакторе."
        )
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignTop)
        hint.setStyleSheet(
            "color: #5A5F68; font-size: 10px; padding-top: 8px;"
        )
        layout.addWidget(hint)

    # ------------------------------------------------------------

    def _add_category_dropdown(
        self,
        layout,
        label: str,
        category: str,
    ) -> None:
        """Кнопка «+ Комната ▼» с меню пресетов."""
        from ..presets import get_registry

        btn = QToolButton()
        btn.setText(f"+ {label}")
        btn.setToolTip(f"Выберите пресет из категории «{label}»")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )
        btn.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextOnly
        )
        btn.setStyleSheet(
            "QToolButton {"
            "  background: #202328;"
            "  color: #E5E5E5;"
            "  border: 1px solid #2A2D33;"
            "  border-radius: 4px;"
            "  padding: 8px 12px;"
            "  text-align: left;"
            "  font-size: 12px;"
            "}"
            "QToolButton:hover {"
            "  background: #2A2D33;"
            "  border-color: #3A3F48;"
            "}"
            "QToolButton::menu-indicator {"
            "  image: none;"
            "  subcontrol-position: right center;"
            "  subcontrol-origin: padding;"
            "  right: 8px;"
            "}"
        )

        menu = QMenu(btn)
        menu.setStyleSheet(
            "QMenu {"
            "  background: #202328;"
            "  color: #E5E5E5;"
            "  border: 1px solid #2A2D33;"
            "  padding: 4px;"
            "}"
            "QMenu::item {"
            "  padding: 6px 20px;"
            "  border-radius: 3px;"
            "}"
            "QMenu::item:selected {"
            "  background: #2A2D33;"
            "}"
        )

        registry = get_registry()
        presets = registry.by_category(category)

        if not presets:
            no_action = menu.addAction("(нет пресетов)")
            no_action.setEnabled(False)
        else:
            for preset in presets:
                action = menu.addAction(preset.name)
                action.setToolTip(preset.id)
                action.triggered.connect(
                    lambda _=False, pid=preset.id:
                        self.preset_requested.emit(pid)
                )

        btn.setMenu(menu)
        layout.addWidget(btn)

    def _add_asset_dropdown(self, layout, label: str) -> None:
        """Кнопка «+ Ассет ▼» — плоский список всех Asset'ов из registry.

        Registry передаётся через set_asset_registry(). Если его нет —
        кнопка неактивна.
        """
        from PySide6.QtWidgets import QToolButton

        btn = QToolButton()
        btn.setText(f"+ {label}")
        btn.setToolTip("Вставить векторный ассет в сцену")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )
        btn.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextOnly
        )
        btn.setStyleSheet(
            "QToolButton {"
            "  background: #202328;"
            "  color: #E5E5E5;"
            "  border: 1px solid #2A2D33;"
            "  border-radius: 4px;"
            "  padding: 8px 12px;"
            "  text-align: left;"
            "  font-size: 12px;"
            "}"
            "QToolButton:hover {"
            "  background: #2A2D33;"
            "  border-color: #3A3F48;"
            "}"
        )

        self._asset_button = btn
        layout.addWidget(btn)

        self._rebuild_asset_menu()

    def _rebuild_asset_menu(self) -> None:
        """Перестраивает меню ассетов из registry."""
        from PySide6.QtWidgets import QMenu

        if not hasattr(self, "_asset_button"):
            return

        menu = QMenu(self._asset_button)
        menu.setStyleSheet(
            "QMenu {"
            "  background: #202328;"
            "  color: #E5E5E5;"
            "  border: 1px solid #2A2D33;"
            "  padding: 4px;"
            "}"
            "QMenu::item {"
            "  padding: 6px 20px;"
            "  border-radius: 3px;"
            "}"
            "QMenu::item:selected {"
            "  background: #2A2D33;"
            "}"
        )

        if self._asset_registry is None or self._asset_registry.count() == 0:
            no_action = menu.addAction("(нет ассетов)")
            no_action.setEnabled(False)
        else:
            for asset in sorted(
                self._asset_registry.all(),
                key=lambda a: (a.name or a.id).lower(),
            ):
                action = menu.addAction(
                    f"{asset.name}  [{asset.type}]"
                )
                action.setToolTip(asset.id)
                action.triggered.connect(
                    lambda _=False, aid=asset.id:
                        self.asset_requested.emit(aid)
                )

        self._asset_button.setMenu(menu)

    def set_asset_registry(self, registry) -> None:
        """Установить registry и обновить меню."""
        self._asset_registry = registry
        self._rebuild_asset_menu()

    def _add_custom_button(
        self,
        layout,
        label: str,
        tooltip: str,
        type_name: str,
    ) -> None:
        btn = QPushButton(label)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton {"
            "  background: #202328;"
            "  color: #E5E5E5;"
            "  border: 1px solid #2A2D33;"
            "  border-radius: 4px;"
            "  padding: 8px 12px;"
            "  text-align: left;"
            "  font-size: 12px;"
            "}"
            "QPushButton:hover {"
            "  background: #2A2D33;"
            "  border-color: #3A3F48;"
            "}"
            "QPushButton:pressed {"
            "  background: #1A1D22;"
            "}"
        )
        btn.clicked.connect(
            lambda _=False, tn=type_name:
                self.element_requested.emit(tn)
        )
        layout.addWidget(btn)
