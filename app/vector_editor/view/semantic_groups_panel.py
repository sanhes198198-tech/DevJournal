"""
SemanticGroupsPanel — правая панель со списком семантических групп Asset'а.

Возможности:
  - список групп текущего Asset'а;
  - Add / Edit / Delete;
  - клик по группе → сигнал group_selected(group_id);
  - groups_changed() — после любого изменения.

Panel не знает про сцену. Выделенные node_ids приходят
через set_selected_node_ids() из editor'а.
"""

from __future__ import annotations

import copy

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
    QToolButton,
    QMenu,
    QMessageBox,
)

from .semantic_group_dialog import SemanticGroupDialog
from .auto_rule_dialog import AutoRuleDialog
from ..model.analysis import (
    AUTO_GROUP_TYPES,
    generate_auto_group,
)
from ..model.semantic_group import SemanticGroup


class SemanticGroupsPanel(QWidget):
    """Панель семантических групп."""

    group_selected = Signal(str)   # group_id
    groups_changed = Signal()      # после add/edit/delete

    WIDTH = 260

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedWidth(self.WIDTH)

        self._asset = None
        self._selected_node_ids: list[str] = []
        # V16: буфер скопированного auto_rule
        self._rule_clipboard: dict | None = None

        self._build_ui()

    # ------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Группы")
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

        # Инфо: сколько узлов выделено
        self._selection_info = QLabel("Выделено узлов: 0")
        self._selection_info.setStyleSheet(
            "color: #858B93; font-size: 10px;"
        )
        layout.addWidget(self._selection_info)

        # Кнопки
        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(4)

        self._btn_add = QPushButton("+")
        self._btn_add.setToolTip("Создать группу из выделенных узлов")
        self._btn_add.setFixedWidth(32)
        self._btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_add.clicked.connect(self._on_add)
        buttons.addWidget(self._btn_add)

        self._btn_edit = QPushButton("Изменить")
        self._btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_edit.clicked.connect(self._on_edit)
        buttons.addWidget(self._btn_edit, 1)

        self._btn_add_sel = QPushButton("Дополнить")
        self._btn_add_sel.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_add_sel.setToolTip(
            "Добавить выделенные в сцене узлы к выбранной группе"
        )
        self._btn_add_sel.clicked.connect(self._on_add_selected)
        buttons.addWidget(self._btn_add_sel)

        self._btn_del = QPushButton("Удалить")
        self._btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_del.clicked.connect(self._on_delete)
        buttons.addWidget(self._btn_del)

        # V9c: кнопка правила авто-размножения
        self._btn_rule = QPushButton("⚙ Правило")
        self._btn_rule.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_rule.setToolTip(
            "Правило авто-размножения точек группы (нужна "
            "группа с ровно одной extra-точкой-шаблоном)"
        )
        self._btn_rule.clicked.connect(self._on_rule)
        buttons.addWidget(self._btn_rule)

        self._style_button(self._btn_add)
        self._style_button(self._btn_edit)
        self._style_button(self._btn_add_sel)
        self._style_button(self._btn_del)
        self._style_button(self._btn_rule)

        layout.addLayout(buttons)

        # V16: вторая строка — копирование правил
        buttons2 = QHBoxLayout()
        buttons2.setContentsMargins(0, 0, 0, 0)
        buttons2.setSpacing(4)

        self._btn_copy_rule = QPushButton("📋 Скопировать правило")
        self._btn_copy_rule.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_copy_rule.setToolTip(
            "Скопировать auto_rule выбранной группы"
        )
        self._btn_copy_rule.clicked.connect(self._on_copy_rule)
        buttons2.addWidget(self._btn_copy_rule, 1)

        self._btn_paste_rule = QPushButton("📋 Вставить")
        self._btn_paste_rule.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_paste_rule.setToolTip(
            "Применить скопированное правило к выбранной группе"
        )
        self._btn_paste_rule.clicked.connect(self._on_paste_rule)
        buttons2.addWidget(self._btn_paste_rule)

        self._style_button(self._btn_copy_rule)
        self._style_button(self._btn_paste_rule)

        layout.addLayout(buttons2)

        # ============================================================
        # АВТО-ГРУППЫ
        # ============================================================
        self._btn_auto = QToolButton()
        self._btn_auto.setText("⚡ Авто")
        self._btn_auto.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )
        self._btn_auto.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_auto.setToolTip(
            "Сгенерировать группу по геометрии контура"
        )

        menu = QMenu(self._btn_auto)
        for kind, label, slug in AUTO_GROUP_TYPES:
            action = menu.addAction(label)
            # default-аргументы, чтобы не поймать замыкание
            action.triggered.connect(
                lambda _checked=False, k=kind, l=label, s=slug:
                self._on_auto_group(k, l, s)
            )

        self._btn_auto.setMenu(menu)
        self._style_button(self._btn_auto)
        layout.addWidget(self._btn_auto)

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

    # ------------------------------------------------------------

    def set_asset(self, asset) -> None:
        """Установить текущий Asset (или None)."""
        self._asset = asset
        self.refresh()

    def set_selected_node_ids(self, node_ids: list[str]) -> None:
        """Обновить список выделенных узлов (для создания новой группы)."""
        self._selected_node_ids = list(node_ids or [])
        n = len(self._selected_node_ids)
        self._selection_info.setText(f"Выделено узлов: {n}")
        self._btn_add.setEnabled(n > 0)

    # ------------------------------------------------------------

    def refresh(self) -> None:
        """Перестроить список групп."""
        self._list.clear()

        if self._asset is None:
            placeholder = QListWidgetItem("— нет Asset'а —")
            placeholder.setFlags(
                placeholder.flags() & ~Qt.ItemFlag.ItemIsSelectable
            )
            self._list.addItem(placeholder)
            self._update_buttons()
            return

        groups = list(self._asset.semantic_groups.values())
        if not groups:
            placeholder = QListWidgetItem("— нет групп —")
            placeholder.setFlags(
                placeholder.flags() & ~Qt.ItemFlag.ItemIsSelectable
            )
            self._list.addItem(placeholder)
            self._update_buttons()
            return

        for g in sorted(groups, key=lambda x: (x.label or x.name).lower()):
            rule_mark = " ⚙" if getattr(g, "auto_rule", None) else ""
            text = f"{g.label}  ({len(g.node_ids)} узлов){rule_mark}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, g.id)
            self._list.addItem(item)

        self._update_buttons()

    def clear_selection(self) -> None:
        """Снять выделение с текущего item (без эмитов)."""
        self._list.clearSelection()
        self._update_buttons()

    def _update_buttons(self) -> None:
        has_asset = self._asset is not None
        has_groups = has_asset and len(self._asset.semantic_groups) > 0
        has_selection = self._list.currentItem() is not None

        self._btn_add.setEnabled(
            has_asset and len(self._selected_node_ids) > 0
        )
        self._btn_edit.setEnabled(has_groups and has_selection)
        self._btn_del.setEnabled(has_groups and has_selection)
        self._btn_add_sel.setEnabled(
            has_groups
            and has_selection
            and len(self._selected_node_ids) > 0
        )

        # V9c: активна если выбрана группа с ровно одной
        # extra-точкой-шаблоном (e_* но не e_auto_*)
        self._btn_rule.setEnabled(
            has_groups and has_selection and self._can_set_rule()
        )

        # V16: копирование правил
        has_rule = False
        if has_groups and has_selection:
            gid = self._current_group_id()
            if gid:
                g = self._asset.get_semantic_group(gid)
                if g is not None and g.auto_rule:
                    has_rule = True
        self._btn_copy_rule.setEnabled(has_rule)
        self._btn_paste_rule.setEnabled(
            has_selection and self._rule_clipboard is not None
        )

    def _can_set_rule(self) -> bool:
        """Проверить, можно ли задать auto_rule для выбранной группы."""
        if self._asset is None:
            return False
        gid = self._current_group_id()
        if gid is None:
            return False
        group = self._asset.get_semantic_group(gid)
        if group is None:
            return False
        # V9c-доп: 1+ не-auto точек разрешены
        non_auto = [
            nid for nid in group.node_ids
            if not nid.startswith("e_auto_")
        ]
        if not non_auto:
            return False
        # Все шаблоны должны быть extra-точками (e_*)
        return all(nid.startswith("e_") for nid in non_auto)

    # ------------------------------------------------------------

    def _current_group_id(self) -> str | None:
        item = self._list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        gid = item.data(Qt.ItemDataRole.UserRole)
        if gid:
            self.group_selected.emit(gid)
        self._update_buttons()

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        # Двойной клик = Edit
        self._on_edit()

    # ------------------------------------------------------------

    def _on_add(self) -> None:
        if self._asset is None:
            return

        if not self._selected_node_ids:
            return

        dlg = SemanticGroupDialog(
            group=None,
            default_node_ids=self._selected_node_ids,
            parent=self,
        )
        if dlg.exec() != SemanticGroupDialog.DialogCode.Accepted:
            return

        if dlg.result_group is None:
            return

        self._asset.add_semantic_group(dlg.result_group)
        self.refresh()
        self.groups_changed.emit()

    def _on_edit(self) -> None:
        if self._asset is None:
            return

        gid = self._current_group_id()
        if gid is None:
            return

        group = self._asset.get_semantic_group(gid)
        if group is None:
            return

        dlg = SemanticGroupDialog(group=group, parent=self)
        if dlg.exec() != SemanticGroupDialog.DialogCode.Accepted:
            return

        # group — уже тот же объект, изменения применены внутри диалога
        self.refresh()
        self.groups_changed.emit()

    def _on_auto_group(
        self, kind: str, label: str, slug: str,
    ) -> None:
        """Сгенерировать группу по геометрии контура.

        Если группа с таким slug уже существует — перезаписываем
        её node_ids и label. Иначе создаём новую.
        """
        if self._asset is None:
            return

        points = self._asset.points()
        node_ids = list(self._asset.geometry.get("node_ids", []))

        generated = generate_auto_group(kind, points, node_ids)
        if not generated:
            QMessageBox.information(
                self,
                "Авто-группа",
                f"Не найдено ни одного узла для группы «{label}».",
            )
            return

        # Ищем существующую группу с таким slug
        existing = None
        for g in self._asset.semantic_groups.values():
            if g.name == slug:
                existing = g
                break

        if existing is not None:
            existing.node_ids = list(generated)
            existing.label = label
        else:
            self._asset.add_semantic_group(
                SemanticGroup(
                    name=slug,
                    label=label,
                    node_ids=list(generated),
                )
            )

        self.refresh()
        self.groups_changed.emit()

    def _on_add_selected(self) -> None:
        """Добавить выделенные узлы (main + extra) к выбранной группе."""
        if self._asset is None:
            return
        gid = self._current_group_id()
        if gid is None:
            return
        group = self._asset.get_semantic_group(gid)
        if group is None:
            return
        if not self._selected_node_ids:
            return

        added = 0
        for nid in self._selected_node_ids:
            if group.add_node(nid):
                added += 1

        if added == 0:
            return

        self.refresh()
        self.groups_changed.emit()

    def _on_copy_rule(self) -> None:
        """V16: скопировать auto_rule выбранной группы в буфер."""
        if self._asset is None:
            return
        gid = self._current_group_id()
        if gid is None:
            return
        group = self._asset.get_semantic_group(gid)
        if group is None or not group.auto_rule:
            return
        self._rule_clipboard = copy.deepcopy(group.auto_rule)
        self._update_buttons()
        self.statusBar_message(
            f"Правило скопировано ({group.label})"
        ) if hasattr(self, "statusBar_message") else None

    def _on_paste_rule(self) -> None:
        """V16: применить скопированное правило к выбранной группе."""
        if self._asset is None or self._rule_clipboard is None:
            return
        gid = self._current_group_id()
        if gid is None:
            return
        group = self._asset.get_semantic_group(gid)
        if group is None:
            return
        group.auto_rule = copy.deepcopy(self._rule_clipboard)
        self.refresh()
        self.groups_changed.emit()

    def _on_delete(self) -> None:
        if self._asset is None:
            return

        gid = self._current_group_id()
        if gid is None:
            return

        group = self._asset.get_semantic_group(gid)
        if group is None:
            return

        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Удалить группу",
            f"Удалить группу «{group.label}»?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self._asset.remove_semantic_group(gid)
        self.refresh()
        # Снять подсветку узлов удалённой группы в сцене
        self.group_selected.emit("")
        self.groups_changed.emit()

    # ------------------------------------------------------------
    # V9c: ПРАВИЛО АВТО-РАЗМНОЖЕНИЯ
    # ------------------------------------------------------------

    def _on_rule(self) -> None:
        """Открыть диалог правила авто-размножения для группы."""
        if self._asset is None:
            return

        gid = self._current_group_id()
        if gid is None:
            return

        group = self._asset.get_semantic_group(gid)
        if group is None:
            return

        if not self._can_set_rule():
            QMessageBox.information(
                self,
                "Правило недоступно",
                "Для настройки правила нужна группа с ровно "
                "одной extra-точкой (шаблоном). Создайте точку "
                "в сцене и добавьте её в группу.",
            )
            return

        all_groups = list(self._asset.semantic_groups.values())
        dlg = AutoRuleDialog(group=group, all_groups=all_groups,
                             parent=self)
        if dlg.exec() != AutoRuleDialog.DialogCode.Accepted:
            return

        # result_rule=None означает "удалить правило"
        if dlg.result_rule is None:
            group.auto_rule = None
        else:
            group.auto_rule = dict(dlg.result_rule)

        self.refresh()
        self.groups_changed.emit()
