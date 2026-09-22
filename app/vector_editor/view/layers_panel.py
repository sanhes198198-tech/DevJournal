"""
LayersPanel — панель слоёв ассета.

Показывает список слоёв, глазок (видимость), кнопки +/−.
На этом этапе (2a) панель только отображает, не переключает контур.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFrame,
)


class LayersPanel(QWidget):
    """Панель слоёв ассета."""

    # (layer_id) — пользователь выбрал слой
    layer_selected = Signal(str)
    # (layer_id, visible)
    layer_visibility_toggled = Signal(str, bool)
    # (layer_id) — удалить
    layer_delete_requested = Signal(str)
    # (layer_id, fillable) — заливать ли текстурой
    layer_fillable_changed = Signal(str, bool)
    # добавить новый слой
    layer_add_requested = Signal()

    WIDTH = 260

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(self.WIDTH)

        self._asset = None
        self._muted = False

        self._build_ui()

    # ------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Слои")
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

        self._list = QListWidget()
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.itemDoubleClicked.connect(self._on_item_double)
        self._list.setStyleSheet(
            "QListWidget {"
            "  background: #181A1E;"
            "  color: #E5E5E5;"
            "  border: 1px solid #2A2D33;"
            "  border-radius: 3px;"
            "  font-size: 11px;"
            "}"
            "QListWidget::item {"
            "  padding: 6px 8px;"
            "}"
            "QListWidget::item:selected {"
            "  background: #2A2D33;"
            "}"
            "QListWidget::item:hover {"
            "  background: #22262C;"
            "}"
        )
        layout.addWidget(self._list, 1)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(4)

        self._btn_add = QPushButton("+")
        self._btn_add.setToolTip("Добавить пустой слой")
        self._btn_add.setFixedWidth(32)
        self._btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_add.clicked.connect(self._on_add)
        buttons.addWidget(self._btn_add)

        self._btn_del = QPushButton("Удалить слой")
        self._btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_del.clicked.connect(self._on_delete)
        buttons.addWidget(self._btn_del, 1)

        self._style_button(self._btn_add)
        self._style_button(self._btn_del)

        layout.addLayout(buttons)

        # V16: чекбокс «Заливать текстурой»
        self._fillable_check = QCheckBox("Заливать текстурой")
        self._fillable_check.setStyleSheet(
            "QCheckBox { color: #E5E5E5; font-size: 11px; "
            "padding-top: 6px; }"
            "QCheckBox:disabled { color: #5A5F68; }"
        )
        self._fillable_check.setToolTip(
            "Если снята — слой не заливается текстурой "
            "(используй для рам поверх окна)."
        )
        self._fillable_check.toggled.connect(
            self._on_fillable_toggled
        )
        self._fillable_check.setEnabled(False)
        layout.addWidget(self._fillable_check)

    @staticmethod
    def _style_button(btn: QPushButton) -> None:
        btn.setStyleSheet(
            "QPushButton {"
            "  background: #202328;"
            "  color: #E5E5E5;"
            "  border: 1px solid #2A2D33;"
            "  border-radius: 3px;"
            "  padding: 5px 8px;"
            "  font-size: 11px;"
            "}"
            "QPushButton:hover { background: #2A2D33; }"
            "QPushButton:disabled { color: #5A5F68; }"
        )

    # ------------------------------------------------------------

    def set_asset(self, asset) -> None:
        """Заполнить список слоёв ассета (или очистить при None)."""
        self._asset = asset
        self.refresh()

    def refresh(self) -> None:
        self._muted = True
        self._list.clear()

        if self._asset is None:
            placeholder = QListWidgetItem("— нет ассета —")
            placeholder.setFlags(
                placeholder.flags() & ~Qt.ItemFlag.ItemIsSelectable
            )
            self._list.addItem(placeholder)
            self._update_buttons()
            self._muted = False
            return

        layers = getattr(self._asset, "layers", []) or []
        if not layers:
            placeholder = QListWidgetItem("— нет слоёв —")
            placeholder.setFlags(
                placeholder.flags() & ~Qt.ItemFlag.ItemIsSelectable
            )
            self._list.addItem(placeholder)
            self._update_buttons()
            self._muted = False
            return

        for l in layers:
            eye = "👁" if l.visible else "·"
            text = f"{eye}  {l.name}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, l.id)
            self._list.addItem(item)

        # Восстановить выделение
        restore = getattr(self, "_restore_selection_id", None)
        if restore:
            for i in range(self._list.count()):
                it = self._list.item(i)
                if it.data(Qt.ItemDataRole.UserRole) == restore:
                    self._list.setCurrentRow(i)
                    break
            self._restore_selection_id = None

        # Синхронизировать чекбокс с текущим выделением
        self._sync_fillable_check()

        self._update_buttons()
        self._muted = False

    def _sync_fillable_check(self) -> None:
        """Обновить состояние чекбокса по текущему выделению."""
        lid = self._current_layer_id()
        self._muted = True
        if lid is None or self._asset is None:
            self._fillable_check.setEnabled(False)
            self._fillable_check.setChecked(True)
        else:
            for l in self._asset.layers:
                if l.id == lid:
                    self._fillable_check.setEnabled(True)
                    self._fillable_check.setChecked(
                        bool(getattr(l, "fillable", True))
                    )
                    break
        self._muted = False

    def _on_fillable_toggled(self, checked: bool) -> None:
        if self._muted:
            return
        lid = self._current_layer_id()
        if lid is None or self._asset is None:
            return
        for l in self._asset.layers:
            if l.id == lid:
                l.fillable = bool(checked)
                self.layer_fillable_changed.emit(
                    str(lid), bool(checked),
                )
                break

    def _update_buttons(self) -> None:
        has_asset = self._asset is not None
        layers = getattr(self._asset, "layers", []) if has_asset else []
        has_selection = self._list.currentItem() is not None

        self._btn_add.setEnabled(has_asset)
        self._btn_del.setEnabled(
            has_asset and has_selection and len(layers) > 1
        )

    # ------------------------------------------------------------

    def _current_layer_id(self) -> str | None:
        it = self._list.currentItem()
        if it is None:
            return None
        return it.data(Qt.ItemDataRole.UserRole)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """Одиночный клик — только выбор слоя."""
        lid = item.data(Qt.ItemDataRole.UserRole)
        if lid:
            self.layer_selected.emit(str(lid))
        self._sync_fillable_check()
        self._update_buttons()

    def _on_item_double(self, item: QListWidgetItem) -> None:
        """Двойной клик — переключить видимость."""
        lid = item.data(Qt.ItemDataRole.UserRole)
        if not lid or self._asset is None:
            return
        for l in self._asset.layers:
            if l.id == lid:
                l.visible = not l.visible
                self.layer_visibility_toggled.emit(
                    str(lid), bool(l.visible),
                )
                break
        # Запомнить выделение и восстановить после refresh
        self._restore_selection_id = str(lid)
        self.refresh()

    def _on_add(self) -> None:
        if self._asset is None:
            return
        self.layer_add_requested.emit()

    def _on_delete(self) -> None:
        lid = self._current_layer_id()
        if lid:
            self.layer_delete_requested.emit(str(lid))