"""
AssetPalette — дерево Asset'ов с папками (вложенные).
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
        # Миграция: у папок без parent → parent = None
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
    """QTreeWidget с кастомным drop для сохранения id."""

    dropped = Signal(list, object)  # (moving_ids, target_id|None)

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

        print(f"[DROP] target={target_id} moving={moving_ids}")

        if not moving_ids:
            event.ignore()
            return

        # Не даём ронять папку в саму себя
        if target_id in moving_ids:
            event.ignore()
            return

        event.accept()
        self.dropped.emit(moving_ids, target_id)


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
            "Drag — переместить"
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

    def _on_dropped(self, moving_ids: list, target_id) -> None:
        print(f"[PALETTE] _on_dropped: moving={moving_ids} target={target_id}")

        # Разделяем на ассеты и папки
        folders = self._folders.get("folders", {})
        placement = self._folders.setdefault("placement", {})

        # target_id может быть ассетом → берём его родителя-папку
        target_folder_id = None
        if target_id:
            if target_id.startswith("f_"):
                target_folder_id = target_id
            else:
                # target — ассет → в его папку
                target_folder_id = placement.get(target_id)

        for mid in moving_ids:
            if mid.startswith("f_"):
                # Перемещение папки — меняем parent
                if mid == target_folder_id:
                    continue
                # Проверка цикла: target_folder_id не должен быть потомком mid
                if target_folder_id is not None:
                    if self._is_descendant(target_folder_id, mid):
                        continue
                folders[mid]["parent"] = target_folder_id
            else:
                # Перемещение ассета
                if target_folder_id:
                    placement[mid] = target_folder_id
                else:
                    placement.pop(mid, None)

        _save_folders(self._folders)
        self._rebuild_tree()
        self._select_by_ids(moving_ids)

    def _is_descendant(self, maybe_child_fid: str, ancestor_fid: str) -> bool:
        """True, если maybe_child находится внутри ancestor (или = ancestor)."""
        folders = self._folders.get("folders", {})
        cur = maybe_child_fid
        seen = set()
        while cur and cur not in seen:
            if cur == ancestor_fid:
                return True
            seen.add(cur)
            fdata = folders.get(cur) or {}
            cur = fdata.get("parent")
        return False

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
        # Запомнить раскрытые папки
        expanded = set()
        def walk_expand(item):
            fid = self._get_item_id(item)
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

        # Индекс: parent_fid → [child_fids]
        children_of = {None: []}
        for fid, fdata in folders.items():
            p = fdata.get("parent")
            if p and p not in folders:
                p = None
            children_of.setdefault(p, []).append(fid)

        # Индекс: folder_fid → [asset_objects]
        assets_in = {fid: [] for fid in folders}
        root_assets = []
        for a in self._assets_cache:
            fid = placement.get(a.id)
            if fid and fid in folders:
                assets_in[fid].append(a)
            else:
                root_assets.append(a)

        # Рекурсивное построение
        def build_folder(fid, parent_item):
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

            # Вложенные папки
            for child_fid in sorted(
                children_of.get(fid, []),
                key=lambda x: (folders[x].get("name") or "").lower(),
            ):
                build_folder(child_fid, item)

            # Ассеты
            for a in sorted(
                assets_in.get(fid, []),
                key=lambda x: (x.name or "").lower(),
            ):
                self._add_asset_item(item, a)

            return item

        # Корневые папки + корневые ассеты
        root_folder_items = {}
        for fid in sorted(
            children_of.get(None, []),
            key=lambda x: (folders[x].get("name") or "").lower(),
        ):
            root_folder_items[fid] = build_folder(fid, None)

        for a in sorted(
            root_assets, key=lambda x: (x.name or "").lower(),
        ):
            self._add_asset_item(None, a)

        # Восстановить раскрытые
        def walk_restore(item):
            fid = self._get_item_id(item)
            if isinstance(fid, str) and fid.startswith("f_") and fid in expanded:
                item.setExpanded(True)
            for j in range(item.childCount()):
                walk_restore(item.child(j))
        for i in range(self._tree.topLevelItemCount()):
            walk_restore(self._tree.topLevelItem(i))

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
        # Если выделена папка — она родитель новой
        parent_fid = None
        folder_ids = self._get_selected_folders()
        if folder_ids:
            parent_fid = folder_ids[0]

        name, ok = QInputDialog.getText(
            self, "Новая папка", "Имя папки:",
        )
        if not ok:
            return
        name = name.strip()
        if not name:
            return

        fid = "f_" + uuid.uuid4().hex[:8]
        self._folders.setdefault("folders", {})[fid] = {
            "name": name,
            "parent": parent_fid,
        }
        _save_folders(self._folders)
        self._rebuild_tree()

    def _folder_size(self, fid: str) -> dict:
        """Сколько вложенных папок и ассетов внутри (рекурсивно)."""
        folders = self._folders.get("folders", {})
        placement = self._folders.get("placement", {})

        n_folders = 0
        n_assets = 0

        def walk(f):
            nonlocal n_folders, n_assets
            for cfid, cfdata in folders.items():
                if cfdata.get("parent") == f:
                    n_folders += 1
                    walk(cfid)
            for aid, pfid in placement.items():
                if pfid == f:
                    n_assets += 1

        walk(fid)
        return {"folders": n_folders, "assets": n_assets}

    def _on_delete_clicked(self) -> None:
        folder_ids = self._get_selected_folders()
        if folder_ids:
            # Посчитать содержимое
            total_folders = 0
            total_assets = 0
            for fid in folder_ids:
                sz = self._folder_size(fid)
                total_folders += 1 + sz["folders"]
                total_assets += sz["assets"]

            msg = f"Удалить {len(folder_ids)} папок?"
            if total_folders > len(folder_ids) or total_assets > 0:
                msg += (
                    f"\n\nВнутри: {total_folders - len(folder_ids)} "
                    f"вложенных папок, {total_assets} ассетов.\n"
                    f"Ассеты вернутся в корень."
                )

            reply = QMessageBox.question(
                self, "Удалить папки", msg,
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            folders = self._folders.get("folders", {})
            placement = self._folders.get("placement", {})

            # Собрать все вложенные папки
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

            # Ассеты из удалённых папок → в корень
            for aid, pfid in list(placement.items()):
                if pfid in to_remove:
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
                    "Новая папка внутри",
                    lambda: self._new_folder_inside(nid),
                )
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
        folders[fid] = {
            "name": name.strip(),
            "parent": parent_fid,
        }
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