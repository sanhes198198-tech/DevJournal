"""
ModeTabs — табы переключения между представлениями.

[План] [Фасад] [Разрез]

В M0 активен только «План». Остальные — disabled.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QTabBar,
    QHBoxLayout,
    QWidget,
)


MODE_PLAN = "plan"
MODE_FACADE = "facade"
MODE_SECTION = "section"


class ModeTabs(QWidget):
    """Табы режимов отображения."""

    mode_changed = Signal(str)

    HEIGHT = 32

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedHeight(self.HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QTabBar()
        self._tabs.addTab("План")
        self._tabs.addTab("Фасад")
        self._tabs.addTab("Разрез")

        # M0: только «План»
        self._tabs.setTabEnabled(1, False)
        self._tabs.setTabEnabled(2, False)
        self._tabs.setCurrentIndex(0)

        self._tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self._tabs)

    def current_mode(self) -> str:
        idx = self._tabs.currentIndex()
        if idx == 0:
            return MODE_PLAN
        if idx == 1:
            return MODE_FACADE
        if idx == 2:
            return MODE_SECTION
        return MODE_PLAN

    def set_mode(self, mode: str) -> None:
        mapping = {
            MODE_PLAN: 0,
            MODE_FACADE: 1,
            MODE_SECTION: 2,
        }
        idx = mapping.get(mode, 0)
        self._tabs.setCurrentIndex(idx)

    def _on_tab_changed(self, idx: int) -> None:
        self.mode_changed.emit(self.current_mode())
