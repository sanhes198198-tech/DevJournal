"""
AssetBrowser — левая панель Vector Editor.
Дерево с папками (общий _folders.json с Constructor).
Показывает только простые ассеты, композиты скрыты.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from PySide6.QtCore import Qt, Signal
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
        for fid, fdata in data["folders"].items():
            if not isinstance(fdata, dict):
                data["folders"][fid] = {"name": "Папка", "parent": None}
            else:
                fdata.setdefault("parent", None)
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
    dropped = Signal(list, object)

    def dropEvent(self, event) -> None:
        target = self.itemAt(event.position().toPoint())
        target_id = None
        if target is not None:
            target_id = target.data(0, Qt.ItemDataRole.UserRole)

        moving_ids = []
        for it in self.selectedItems():
            nid = it.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(nid, str):
                moving_ids.append(nid)

        if not moving_ids or target_id in moving_ids:
            event.ignore()
            return
        event.accept()
        self.dropped.emit(moving_ids, target_id)


class AssetBrowser(QWidget):
    asset_open_requested = Signal(str)
    asset_delete_requested = Signal(str)
    asset_rename_requested = Signal(str)

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

        title = QLabel("Assets")
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

        self._tree = _AssetTree()
        self._tree.setHeaderHidden(True)
        self._tree.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self._tree.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
        )
        self._tree.setDragEnabled(True)
        self._tree.setAcceptDrops(True)
        self._tree.setDropIndicatorShown(True)
        self._tree.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._tree.itemDoubleClicked.connect(self._on_double)
        self._tree.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._tree.customContextMenuRequested.connect(
            self._on_context_menu
        )
        self._tree.dropped.connect(self._on_dropped)
        self._tree.setStyleSheet(
            "QTreeWidget {"
            "  background: #181A1E;"
            "  color: #E5E5E5;"
            "  border: 1px solid #2A2D33;"
            "  border-radius: 3px;"
            "  font-size: 11px;"
            "}"
            "QTreeWidget::item {"
            "  padding: 4px 6px;"
            "}"
            "QTreeWidget::item:selected {"
            "  background: #2A2D33;"
            "}"
            "QTreeWidget::item:hover {"
            "  background: #22262C;"
            "}"
        )
        layout.addWidget(self._tree, 1)

        hint = QLabel(
            "Двойной клик — открыть\n"
            "F2 или ПКМ — переименовать\n"
            "Drag — переместить"
        )
        hint.setStyleSheet(
            "color: #5A5F68; font-size: 10px; padding-top: 4px;"
        )
        layout.addWidget(hint)

        row = QHBoxLayout()
        row.setSpacing(4)

        btn_ref = QPushButton("Обновить")
        btn_ref.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ref.clicked.connect(self.refresh)
        self._apply_btn_style(btn_ref)
        row.addWidget(btn_ref)

        btn_folder = QPushButton("+ Папка")
        btn_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_folder.clicked.connect(self._on_new_folder)
        self._apply_btn_style(btn_folder)
        row.addWidget(btn_folder)

        layout.addLayout(row)

    def _apply_btn_style(self, btn) -> None:
        btn.setStyleSheet(
            "QPushButton {"
            "  background: #202328;"
            "  color: #E5E5E5;"
            "  border: 1px solid #2A2D33;"
            "  border-radius: 3px;"
            "  padding: 6px 10px;"
            "  font-size: 11px;"
            "}"
            "QPushButton:hover {"
            "  background: #2A2D33;"
            "}"
        )

    # ------------------------------------------------------------

    def refresh(self) -> None:
        from ..io import list_assets
        self._assets_cache = [
            a for a in list_assets()
            if not getattr(a, "components", None)
        ]
        self._folders = _load_folders()
        self._rebuild_tree()

    def clear_selection(self) -> None:
        self._tree.clearSelection()

    # ------------------------------------------------------------

    def _rebuild_tree(self) -> None:
        expanded = set()

        def walk_expand(item):
            fid = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(fid, str) and fid.startswith("f_") and item.isExpanded():
                expanded.add(fid)
            for j in range(item.childCount()):
                walk_expand(item.child(j))

        for i in range(self._tree.topLevelItemCount()):
            walk_expand(self._tree.topLevelItem(i))

        self._tree.blockSignals(True)
        self._tree.clear()

        folders = self._folders.get("folders", {})
        placement = self._folders.get("placement", {})

        children_of = {None: []}
        for fid, fdata in folders.items():
            p = fdata.get("parent")
            if p and p not in folders:
                p = None
            children_of.setdefault(p, []).append(fid)

        assets_in = {fid: [] for fid in folders}
        root_assets = []
        for a in self._assets_cache:
            fid = placement.get(a.id)
            if fid and fid in folders:
                assets_in[fid].append(a)
            else:
                root_assets.append(a)

        # Скрыть пустые папки (нет ассетов и нет непустых вложенных)
        def _has_content(fid):
            if assets_in.get(fid):
                return True
            for cfid in children_of.get(fid, []):
                if _has_content(cfid):
                    return True
            return False

        visible_folders = {
            fid for fid in folders if _has_content(fid)
        }

        def build_folder(fid, parent_item):
            if fid not in visible_folders:
                return None
            fdata = folders[fid]
            item = QTreeWidgetItem([fdata.get("name", "Папка")])
            item.setData(0, Qt.ItemDataRole.UserRole, fid)
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDropEnabled
                | Qt.ItemFlag.ItemIsDragEnabled
            )
            if parent_item is None:
                self._tree.addTopLevelItem(item)
            else:
                parent_item.addChild(item)

            for child_fid in sorted(
                children_of.get(fid, []),
                key=lambda x: (folders[x].get("name") or "").lower(),
            ):
                if child_fid in visible_folders:
                    build_folder(child_fid, item)

            for a in sorted(
                assets_in.get(fid, []),
                key=lambda x: (x.name or "").lower(),
            ):
                self._add_asset_item(item, a)

            return item

        for fid in sorted(
            children_of.get(None, []),
            key=lambda x: (folders[x].get("name") or "").lower(),
        ):
            if fid in visible_folders:
                build_folder(fid, None)

        for a in sorted(
            root_assets, key=lambda x: (x.name or "").lower(),
        ):
            self._add_asset_item(None, a)

        def walk_restore(item):
            fid = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(fid, str) and fid.startswith("f_") and fid in expanded:
                item.setExpanded(True)
            for j in range(item.childCount()):
                walk_restore(item.child(j))

        for i in range(self._tree.topLevelItemCount()):
            walk_restore(self._tree.topLevelItem(i))

        self._tree.blockSignals(False)

    def _add_asset_item(self, parent, asset) -> None:
        text = f"{asset.name}  [{asset.type}]"
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

    def _get_item_id(self, item):
        return item.data(0, Qt.ItemDataRole.UserRole)

    def _is_folder(self, item) -> bool:
        nid = self._get_item_id(item)
        return isinstance(nid, str) and nid.startswith("f_")

    def _selected_assets(self):
        ids = []
        for it in self._tree.selectedItems():
            nid = self._get_item_id(it)
            if isinstance(nid, str) and not nid.startswith("f_"):
                ids.append(nid)
        return ids

    def _selected_folders(self):
        ids = []
        for it in self._tree.selectedItems():
            nid = self._get_item_id(it)
            if isinstance(nid, str) and nid.startswith("f_"):
                ids.append(nid)
        return ids

    # ------------------------------------------------------------

    def _on_double(self, item, col) -> None:
        if self._is_folder(item):
            return
        nid = self._get_item_id(item)
        if nid:
            self.asset_open_requested.emit(nid)

    def _on_dropped(self, moving_ids, target_id) -> None:
        folders = self._folders.get("folders", {})
        placement = self._folders.setdefault("placement", {})

        target_folder_id = None
        if target_id:
            if target_id.startswith("f_"):
                target_folder_id = target_id
            else:
                target_folder_id = placement.get(target_id)

        for mid in moving_ids:
            if mid.startswith("f_"):
                if mid == target_folder_id:
                    continue
                if target_folder_id is not None:
                    if self._is_descendant(target_folder_id, mid):
                        continue
                folders[mid]["parent"] = target_folder_id
            else:
                if target_folder_id:
                    placement[mid] = target_folder_id
                else:
                    placement.pop(mid, None)

        _save_folders(self._folders)
        self._rebuild_tree()
        self._select_by_ids(moving_ids)

    def _is_descendant(self, maybe_child, ancestor) -> bool:
        folders = self._folders.get("folders", {})
        cur = maybe_child
        seen = set()
        while cur and cur not in seen:
            if cur == ancestor:
                return True
            seen.add(cur)
            fdata = folders.get(cur) or {}
            cur = fdata.get("parent")
        return False

    def _select_by_ids(self, ids) -> None:
        def walk(item):
            if self._get_item_id(item) in ids:
                item.setSelected(True)
            for j in range(item.childCount()):
                walk(item.child(j))

        for i in range(self._tree.topLevelItemCount()):
            walk(self._tree.topLevelItem(i))

    # ------------------------------------------------------------

    def _on_new_folder(self) -> None:
        parent_fid = None
        folder_ids = self._selected_folders()
        if folder_ids:
            parent_fid = folder_ids[0]

        name, ok = QInputDialog.getText(
            self, "Новая папка", "Имя папки:",
        )
        if not ok or not name.strip():
            return

        fid = "f_" + uuid.uuid4().hex[:8]
        self._folders.setdefault("folders", {})[fid] = {
            "name": name.strip(),
            "parent": parent_fid,
        }
        _save_folders(self._folders)
        self._rebuild_tree()

    def _new_folder_inside(self, parent_fid: str) -> None:
        folders = self._folders.get("folders", {})
        if parent_fid not in folders:
            return
        name, ok = QInputDialog.getText(
            self, "Новая папка", "Имя папки:",
        )
        if not ok or not name.strip():
            return
        fid = "f_" + uuid.uuid4().hex[:8]
        folders[fid] = {"name": name.strip(), "parent": parent_fid}
        _save_folders(self._folders)
        self._rebuild_tree()

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

    def _delete_folders(self, folder_ids) -> None:
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

        folders = self._folders.get("folders", {})
        placement = self._folders.get("placement", {})

        to_remove = set()

        def collect(fid):
            to_remove.add(fid)
            for cfid, cfdata in folders.items():
                if cfdata.get("parent") == fid:
                    collect(cfid)

        for fid in folder_ids:
            collect(fid)

        for fid in to_remove:
            folders.pop(fid, None)
        for aid, pfid in list(placement.items()):
            if pfid in to_remove:
                placement.pop(aid, None)

        _save_folders(self._folders)
        self._rebuild_tree()

    def _on_context_menu(self, pos) -> None:
        item = self._tree.itemAt(pos)
        menu = QMenu(self)

        if item is None:
            menu.addAction("Новая папка", self._on_new_folder)
        elif self._is_folder(item):
            fid = self._get_item_id(item)
            menu.addAction(
                "Новая папка внутри",
                lambda: self._new_folder_inside(fid),
            )
            menu.addAction(
                "Переименовать",
                lambda: self._rename_folder(fid),
            )
            menu.addAction(
                "Удалить",
                lambda: self._delete_folders([fid]),
            )
        else:
            aid = self._get_item_id(item)
            menu.addAction(
                "Открыть",
                lambda: self.asset_open_requested.emit(aid),
            )
            menu.addAction(
                "Переименовать",
                lambda: self.asset_rename_requested.emit(aid),
            )
            menu.addAction(
                "Удалить",
                lambda: self.asset_delete_requested.emit(aid),
            )

        if menu.actions():
            menu.exec(self._tree.mapToGlobal(pos))

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_F2:
            asset_ids = self._selected_assets()
            if asset_ids:
                self.asset_rename_requested.emit(asset_ids[0])
                return
            folder_ids = self._selected_folders()
            if folder_ids:
                self._rename_folder(folder_ids[0])
                return
        super().keyPressEvent(event)