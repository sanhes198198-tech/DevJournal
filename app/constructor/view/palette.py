"""
AssetPalette — дерево Asset'ов с папками для Constructor.
Структура папок хранится в _folders.json.
"""
from __future__ import annotations
import json
import uuid
from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QLabel, QTreeWidget, QTreeWidgetItem, QPushButton,
    QVBoxLayout, QHBoxLayout, QWidget, QFrame, QMenu,
    QInputDialog, QMessageBox, QAbstractItemView,
)


FOLDERS_FILE = Path("app/vector_editor/assets/_folders.json")


def _load_folders() -> dict:
    if not FOLDERS_FILE.exists():
        return {"folders": {}, "placement": {}}
    try:
        data = json.loads(FOLDERS_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"folders": {}, "placement": {}}
        data.setdefault("folders", {})
        data.setdefault("placement", {})
        return data
    except Exception:
        return {"folders": {}, "placement": {}}


def _save_folders(data: dict) -> None:
    try:
        FOLDERS_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


class _AssetTree(QTreeWidget):
    """QTreeWidget с кастомным drop для сохранения id."""

    dropped = Signal(list, object)  # (moving_ids, target_folder_id|None)

    def dropEvent(self, event) -> None:
        target = self.itemAt(event.position().toPoint())

        target_folder_id = None
        if target is not None:
            nid = target.data(0, Qt.ItemDataRole.UserRole)
            if nid and isinstance(nid, str) and nid.startswith("f_"):
                target_folder_id = nid
            elif nid:
                parent = target.parent()
                if parent is not None:
                    pfid = parent.data(0, Qt.ItemDataRole.UserRole)
                    if pfid and isinstance(pfid, str) and pfid.startswith("f_"):
                        target_folder_id = pfid

        moving_ids = []
        for it in self.selectedItems():
            nid = it.data(0, Qt.ItemDataRole.UserRole)
            if nid and isinstance(nid, str) and not nid.startswith("f_"):
                moving_ids.append(nid)

        print(f"[DROP] target_folder={target_folder_id} moving={moving_ids}")

        if not moving_ids:
            event.ignore()
            return

        # НЕ вызываем super().dropEvent — сами управляем
        event.accept()
        self.dropped.emit(moving_ids, target_folder_id)


class AssetPalette(QWidget):
    asset_selected = Signal(str)
    asset_add_requested = Signal(str)
    refresh_requested = Signal()
    delete_requested = Signal(list)
    rename_requested = Signal(str, str)
    WIDTH = 280

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(self.WIDTH)
        self._folders = _load_folders()
        self._assets_cache = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Ассеты")
        title.setStyleSheet(
            "font-weight: 600; font-size: 12px; color: #1A1A1A;")
        layout.addWidget(title)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        self._tree = _AssetTree()
        self._tree.setHeaderHidden(True)
        self._tree.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self._tree.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
        )
        self._tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._tree.setDragEnabled(True)
        self._tree.setAcceptDrops(True)
        self._tree.setDropIndicatorShown(True)
        self._tree.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._tree.itemClicked.connect(self._on_clicked)
        self._tree.itemDoubleClicked.connect(self._on_double)
        self._tree.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._tree.customContextMenuRequested.connect(
            self._on_context_menu
        )
        self._tree.dropped.connect(self._on_dropped)
        layout.addWidget(self._tree, 1)

        hint = QLabel(
            "Двойной клик — добавить\n"
            "F2 или ПКМ — переименовать\n"
            "Drag — переместить в папку"
        )
        hint.setStyleSheet("color: #888888; font-size: 10px;")
        layout.addWidget(hint)

        row = QHBoxLayout()
        row.setSpacing(4)

        btn_ref = QPushButton("Обновить")
        btn_ref.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ref.clicked.connect(self.refresh_requested.emit)
        row.addWidget(btn_ref)

        btn_folder = QPushButton("+ Папка")
        btn_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_folder.clicked.connect(self._on_new_folder)
        row.addWidget(btn_folder)

        layout.addLayout(row)

        btn_del = QPushButton("Удалить выбранные")
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet("color: #C0392B;")
        btn_del.clicked.connect(self._on_delete_clicked)
        layout.addWidget(btn_del)

    def _on_dropped(self, moving_ids: list, target_folder_id) -> None:
        print(f"[PALETTE] _on_dropped: moving={moving_ids} "
              f"target={target_folder_id}")
        placement = self._folders.setdefault("placement", {})
        for aid in moving_ids:
            if target_folder_id:
                placement[aid] = target_folder_id
            else:
                placement.pop(aid, None)
        _save_folders(self._folders)
        self._rebuild_tree()
        self._select_by_ids(moving_ids)

    def set_assets(self, assets: list) -> None:
        self._assets_cache = list(assets)
        self._folders = _load_folders()
        self._rebuild_tree()

    def clear_selection(self) -> None:
        self._tree.clearSelection()

    def _get_item_id(self, item):
        return item.data(0, Qt.ItemDataRole.UserRole)

    def _add_asset_item(self, parent, asset) -> None:
        is_comp = bool(getattr(asset, "components", None))
        icon = "📦 " if is_comp else ""
        text = f"{icon}{asset.name}  [{asset.type}]"
        item = QTreeWidgetItem([text])
        item.setData(0, Qt.ItemDataRole.UserRole, asset.id)
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsDragEnabled
        )
        if parent is None:
            self._tree.addTopLevelItem(item)
        else:
            parent.addChild(item)

    def _rebuild_tree(self) -> None:
        expanded = set()
        for i in range(self._tree.topLevelItemCount()):
            it = self._tree.topLevelItem(i)
            if it.isExpanded():
                fid = self._get_item_id(it)
                if isinstance(fid, str) and fid.startswith("f_"):
                    expanded.add(fid)

        self._tree.blockSignals(True)
        self._tree.clear()

        folders = self._folders.get("folders", {})
        placement = self._folders.get("placement", {})

        assets_in_folder = {fid: [] for fid in folders}
        root_assets = []
        for a in self._assets_cache:
            fid = placement.get(a.id)
            if fid and fid in folders:
                assets_in_folder[fid].append(a)
            else:
                root_assets.append(a)

        folder_items = {}
        for fid, fdata in sorted(
            folders.items(),
            key=lambda kv: (kv[1].get("name") or "").lower(),
        ):
            item = QTreeWidgetItem([fdata.get("name", "Папка")])
            item.setData(0, Qt.ItemDataRole.UserRole, fid)
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDropEnabled
                | Qt.ItemFlag.ItemIsDragEnabled
            )
            self._tree.addTopLevelItem(item)
            folder_items[fid] = item

        for fid, items in assets_in_folder.items():
            parent = folder_items.get(fid)
            if parent is None:
                continue
            for a in items:
                self._add_asset_item(parent, a)

        for a in root_assets:
            self._add_asset_item(None, a)

        for fid in expanded:
            parent = folder_items.get(fid)
            if parent is not None:
                parent.setExpanded(True)

        self._tree.blockSignals(False)

    def _get_selected_assets(self) -> list:
        ids = []
        for it in self._tree.selectedItems():
            nid = self._get_item_id(it)
            if isinstance(nid, str) and not nid.startswith("f_"):
                ids.append(nid)
        return ids

    def _get_selected_folders(self) -> list:
        ids = []
        for it in self._tree.selectedItems():
            nid = self._get_item_id(it)
            if isinstance(nid, str) and nid.startswith("f_"):
                ids.append(nid)
        return ids

    def _on_clicked(self, item, col) -> None:
        nid = self._get_item_id(item)
        if isinstance(nid, str) and not nid.startswith("f_"):
            self.asset_selected.emit(nid)

    def _on_double(self, item, col) -> None:
        nid = self._get_item_id(item)
        if isinstance(nid, str) and not nid.startswith("f_"):
            self.asset_add_requested.emit(nid)

    def _on_new_folder(self) -> None:
        name, ok = QInputDialog.getText(
            self, "Новая папка", "Имя папки:",
        )
        if not ok:
            return
        name = name.strip()
        if not name:
            return

        fid = "f_" + uuid.uuid4().hex[:8]
        self._folders.setdefault("folders", {})[fid] = {"name": name}
        _save_folders(self._folders)
        self._rebuild_tree()

    def _on_delete_clicked(self) -> None:
        folder_ids = self._get_selected_folders()
        if folder_ids:
            reply = QMessageBox.question(
                self, "Удалить папки",
                f"Удалить {len(folder_ids)} папок? "
                f"Содержимое вернётся в корень.",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            for fid in folder_ids:
                self._folders.get("folders", {}).pop(fid, None)
                placement = self._folders.get("placement", {})
                for aid, pfid in list(placement.items()):
                    if pfid == fid:
                        placement.pop(aid, None)
            _save_folders(self._folders)
            self._rebuild_tree()
            return

        asset_ids = self._get_selected_assets()
        if asset_ids:
            self.delete_requested.emit(asset_ids)

    def _on_context_menu(self, pos) -> None:
        item = self._tree.itemAt(pos)
        menu = QMenu(self)

        if item is None:
            menu.addAction("Новая папка", self._on_new_folder)
        else:
            nid = self._get_item_id(item)
            if isinstance(nid, str) and nid.startswith("f_"):
                menu.addAction(
                    "Переименовать папку",
                    lambda: self._rename_folder(nid),
                )
                menu.addAction("Удалить папку", self._on_delete_clicked)
            elif nid:
                menu.addAction(
                    "Переименовать ассет",
                    lambda: self._rename_asset(nid),
                )
                menu.addAction("Удалить", self._on_delete_clicked)

        if menu.actions():
            menu.exec(self._tree.mapToGlobal(pos))

    def _rename_folder(self, fid: str) -> None:
        fdata = self._folders.get("folders", {}).get(fid)
        if not fdata:
            return
        name, ok = QInputDialog.getText(
            self, "Переименовать папку", "Новое имя:",
            text=fdata.get("name", ""),
        )
        if not ok or not name.strip():
            return
        fdata["name"] = name.strip()
        _save_folders(self._folders)
        self._rebuild_tree()

    def _rename_asset(self, aid: str) -> None:
        for a in self._assets_cache:
            if a.id == aid:
                name, ok = QInputDialog.getText(
                    self, "Переименовать ассет", "Новое имя:",
                    text=a.name,
                )
                if not ok or not name.strip():
                    return
                self.rename_requested.emit(aid, name.strip())
                return

    def _select_by_ids(self, ids: list) -> None:
        def walk(item):
            nid = self._get_item_id(item)
            if nid in ids:
                item.setSelected(True)
            for j in range(item.childCount()):
                walk(item.child(j))

        for i in range(self._tree.topLevelItemCount()):
            walk(self._tree.topLevelItem(i))

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_F2:
            asset_ids = self._get_selected_assets()
            if asset_ids:
                self._rename_asset(asset_ids[0])
                return
            folder_ids = self._get_selected_folders()
            if folder_ids:
                self._rename_folder(folder_ids[0])
                return
        super().keyPressEvent(event)