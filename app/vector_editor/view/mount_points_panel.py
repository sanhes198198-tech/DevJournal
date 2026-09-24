"""
MountPointsPanel - панель точек крепления Asset.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QFrame,
    QMessageBox,
)

from .mount_point_dialog import MountPointDialog, ROLE_LABELS
from ..model.mounting import MountPoint


class MountPointsPanel(QWidget):
    """Панель точек крепления."""

    mount_point_selected = Signal(str)
    mount_points_changed = Signal()

    WIDTH = 260

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedWidth(self.WIDTH)
        self._asset = None

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Точки крепления")
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
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
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
        self._btn_add.setToolTip("Создать точку крепления")
        self._btn_add.setFixedWidth(32)
        self._btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_add.clicked.connect(self._on_add)
        buttons.addWidget(self._btn_add)

        self._btn_edit = QPushButton("Изменить")
        self._btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_edit.clicked.connect(self._on_edit)
        buttons.addWidget(self._btn_edit, 1)

        self._btn_del = QPushButton("Удалить")
        self._btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_del.clicked.connect(self._on_delete)
        buttons.addWidget(self._btn_del)

        for b in (self._btn_add, self._btn_edit, self._btn_del):
            self._style_button(b)

        layout.addLayout(buttons)

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
            "QPushButton:hover {"
            "  background: #2A2D33;"
            "}"
            "QPushButton:disabled {"
            "  color: #5A5F68;"
            "}"
        )

    def set_asset(self, asset) -> None:
        self._asset = asset
        self.refresh()

    def refresh(self) -> None:
        self._list.clear()

        if self._asset is None:
            ph = QListWidgetItem("— нет Asset'а —")
            ph.setFlags(ph.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self._list.addItem(ph)
            self._update_buttons()
            return

        mps = list(getattr(self._asset, "mountpoints", []) or [])
        if not mps:
            ph = QListWidgetItem("— нет точек —")
            ph.setFlags(ph.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self._list.addItem(ph)
            self._update_buttons()
            return

        for mp in mps:
            role_label = "?"
            for role, label in ROLE_LABELS:
                if role == mp.role:
                    role_label = label
                    break

            d = mp.distribution
            if d.is_simple():
                dist = ""
            else:
                dist = f" ×{d.count_x}×{d.count_y}"

            text = (
                f"{role_label}{dist}  "
                f"({mp.position[0]:.1f}, {mp.position[1]:.1f})"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, mp.id)
            self._list.addItem(item)

        self._update_buttons()

    def clear_selection(self) -> None:
        self._list.clearSelection()
        self._update_buttons()

    def _update_buttons(self) -> None:
        has_asset = self._asset is not None
        has_mps = (
            has_asset
            and len(getattr(self._asset, "mountpoints", []) or []) > 0
        )
        has_sel = self._list.currentItem() is not None
        self._btn_add.setEnabled(has_asset)
        self._btn_edit.setEnabled(has_mps and has_sel)
        self._btn_del.setEnabled(has_mps and has_sel)

    def _current_mp_id(self) -> str | None:
        item = self._list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _find_mp(self, mp_id: str) -> MountPoint | None:
        if self._asset is None:
            return None
        for mp in getattr(self._asset, "mountpoints", []) or []:
            if mp.id == mp_id:
                return mp
        return None

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        mp_id = item.data(Qt.ItemDataRole.UserRole)
        if mp_id:
            self.mount_point_selected.emit(mp_id)
        self._update_buttons()

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        self._on_edit()

    def _on_add(self) -> None:
        if self._asset is None:
            return

        # V22: дефолт = центр bbox asset.geometry
        default_pos = (0.0, 0.0)
        try:
            pts = self._asset.points()
            if pts:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                default_pos = (
                    (min(xs) + max(xs)) / 2.0,
                    (min(ys) + max(ys)) / 2.0,
                )
        except Exception:
            pass

        dlg = MountPointDialog(
            default_position=default_pos,
            parent=self,
        )
        if dlg.exec() != MountPointDialog.DialogCode.Accepted:
            return
        if dlg.result_mountpoint is None:
            return

        if not hasattr(self._asset, "mountpoints"):
            self._asset.mountpoints = []
        self._asset.mountpoints.append(dlg.result_mountpoint)

        self.refresh()
        self.mount_points_changed.emit()

    def _on_edit(self) -> None:
        mp_id = self._current_mp_id()
        if mp_id is None:
            return
        mp = self._find_mp(mp_id)
        if mp is None:
            return

        dlg = MountPointDialog(mountpoint=mp, parent=self)
        if dlg.exec() != MountPointDialog.DialogCode.Accepted:
            return

        self.refresh()
        self.mount_points_changed.emit()

    def _on_delete(self) -> None:
        mp_id = self._current_mp_id()
        if mp_id is None:
            return
        mp = self._find_mp(mp_id)
        if mp is None:
            return

        reply = QMessageBox.question(
            self,
            "Удалить точку",
            f"Удалить точку {mp_id}?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._asset.mountpoints = [
            m for m in self._asset.mountpoints if m.id != mp_id
        ]
        self.refresh()
        self.mount_point_selected.emit("")
        self.mount_points_changed.emit()
