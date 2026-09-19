"""
Инспектор свойств выбранного узла.

Правая панель редактора диалогов.

ВАЖНО: Inspector НЕ мутирует модель напрямую.
Все изменения идут через command_sink → QUndoStack → Command.redo().

При заполнении UI из модели используется self._updating
+ blockSignals, чтобы не порождать «фантомные» команды.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QFrame,
    QRadioButton,
    QComboBox,
)

from ..model import (
    StartNode,
    ReplyNode,
    ChoiceNode,
    EndNode,
)
from ..commands import (
    ChangePropertyCommand,
    AddOptionCommand,
    RemoveOptionCommand,
    MoveOptionCommand,
)
from ..ids import generate_option_id
from ..model.node import ChoiceOption
from ..model.condition import Condition, ConditionGroup
from .condition_dialog import ConditionDialog
from .effect_dialog import EffectDialog


# =========================================================
# ИНСПЕКТОР
# =========================================================

class DialogueInspector(QWidget):
    """Правая панель редактирования свойств узла."""

    node_changed = Signal(str)
    connections_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.dialogue = None
        self.current_node_id = None

        # Защита от циклов
        self._updating = False

        # command_sink — callable, куда кидаем QUndoCommand.
        # В DialogueEditorWindow: sink = undo_stack.push.
        # Fallback: применяем команду сразу через .redo().
        self._command_sink = None

        # ProjectData — справочник персонажей / переменных / флагов.
        # Может быть None, если ещё не загружен.
        self.project_data = None

        self._build_ui()

    # =========================================================
    # COMMAND SINK
    # =========================================================

    def set_command_sink(self, sink):
        """
        sink — callable(command) или None.
        Если None — команды применяются сразу (без undo).
        """
        self._command_sink = sink

    def _push(self, command):
        """Отправляет команду в sink либо применяет сразу."""
        if self._command_sink is not None:
            self._command_sink(command)
        else:
            command.redo()

    # =========================================================
    # UI КАРКАС
    # =========================================================

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(6)

        self.title_label = QLabel("Свойства")
        self.title_label.setStyleSheet(
            "font-weight: 600; font-size: 13px;"
        )
        outer.addWidget(self.title_label)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        outer.addWidget(line)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 6, 0, 0)
        self.content_layout.setSpacing(10)
        self.content_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.content)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        outer.addWidget(scroll, 1)

        self._show_placeholder()

    def _clear_content(self):
        while self.content_layout.count() > 0:
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    # =========================================================
    # READ-ONLY БЛОКИ (архитектурный контракт)
    # =========================================================

    def _add_row(self, label_text, widget):
        """Добавляет строку 'label + widget'."""
        label = QLabel(label_text)
        label.setStyleSheet(
            "color: #858B93; font-size: 11px; padding-top: 4px;"
        )
        self.content_layout.addWidget(label)
        self.content_layout.addWidget(widget)

    def _add_section_header(self, text):
        label = QLabel(text)
        label.setStyleSheet(
            "color: #999; font-size: 10px; "
            "font-weight: 600; padding-top: 10px;"
        )
        self.content_layout.addWidget(label)

    def _add_presentation_block(self, node):
        """Read-only: presentation у ReplyNode."""

        self._add_section_header("PRESENTATION (скоро)")

        if node.presentation:
            for key, val in node.presentation.items():
                row = QLabel(f"{key}: {val}")
                row.setStyleSheet(
                    "color: #666; font-size: 11px; padding-left: 8px;"
                )
                self.content_layout.addWidget(row)
        else:
            hint = QLabel(
                "Портрет, эмоция, позиция — "
                "будут редактироваться в след. версии."
            )
            hint.setWordWrap(True)
            hint.setStyleSheet(
                "color: #aaa; font-size: 10px; padding-left: 8px;"
            )
            self.content_layout.addWidget(hint)

    def _add_outcome_block(self, node):
        """Read-only: outcome_type / outcome_id у EndNode."""

        self._add_section_header("OUTCOME")

        # v3: outcome_type + outcome_id
        outcome_type = getattr(
            node, "outcome_type", "return_to_game"
        )
        outcome_id = getattr(node, "outcome_id", None)
        target = getattr(node, "target_dialogue_id", None)

        if outcome_type == "return_to_game":
            label_text = "Завершить диалог"
            checked = True
        else:
            label_text = "Перейти в диалог..."
            checked = False

        rb_end = QRadioButton(label_text)
        rb_end.setChecked(checked)
        rb_end.setEnabled(False)
        self.content_layout.addWidget(rb_end)

        # outcome_id
        if outcome_id:
            id_label = QLabel(
                f"outcome_id: {outcome_id}"
            )
            id_label.setStyleSheet(
                "color: #858B93; font-size: 10px; "
                "padding-left: 24px;"
            )
            self.content_layout.addWidget(id_label)

        # target_dialogue_id
        if outcome_type == "start_dialogue" and target:
            target_label = QLabel(
                f"target: {target[:8]}..."
            )
            target_label.setStyleSheet(
                "color: #858B93; font-size: 10px; "
                "padding-left: 24px;"
            )
            self.content_layout.addWidget(target_label)

        hint = QLabel(
            "Редактирование появится в след. версии."
        )
        hint.setStyleSheet(
            "color: #5A5F68; font-size: 10px; padding-top: 4px;"
        )
        self.content_layout.addWidget(hint)

    def _build_option_info(self, opt):
        """
        Read-only info + inline conditions editor.

        Возвращает QWidget-контейнер.
        """
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)

        # --- info-строка ---
        info_parts = []
        if opt.conditions is not None and len(opt.conditions) > 0:
            logic = opt.conditions.logic
            n = len(opt.conditions)
            word = "условие" if n == 1 else "условий"
            info_parts.append(f"conditions: {logic} \u00b7 {n} {word}")
        if opt.effects:
            n = len(opt.effects)
            word = "эффект" if n == 1 else "эффектов"
            info_parts.append(f"effects: {n} {word}")
        if getattr(opt, "is_default", False):
            info_parts.append("default")

        if info_parts:
            info_text = "  [i] " + " \u00b7 ".join(info_parts)
            info_color = "#858B93"
        else:
            info_text = "  [i] Без условий и эффектов"
            info_color = "#5A5F68"

        info_label = QLabel(info_text)
        info_label.setStyleSheet(
            f"color: {info_color}; font-size: 10px; "
            f"padding-left: 24px;"
        )
        v.addWidget(info_label)

        # --- секция Conditions ---
        v.addWidget(self._build_conditions_section(opt))

        # --- секция Effects ---
        v.addWidget(self._build_effects_section(opt))

        return container

    # =========================================================
    # CONDITIONS SECTION
    # =========================================================

    def _build_conditions_section(self, opt):
        """Строит секцию Conditions для одного option."""
        section = QWidget()
        v = QVBoxLayout(section)
        v.setContentsMargins(24, 0, 0, 0)
        v.setSpacing(3)

        # --- Заголовок + управление ---
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(4)

        cond = opt.conditions
        has_conditions = cond is not None and len(cond) > 0

        # Logic toggle (AND/OR) — только если есть 2+ условий
        if has_conditions and len(cond) >= 2:
            logic = cond.logic
            btn_logic = QPushButton(logic)
            btn_logic.setFixedHeight(20)
            btn_logic.setFixedWidth(48)
            btn_logic.setToolTip("Переключить AND/OR")
            btn_logic.setStyleSheet(
                "background: #202328; color: #858B93; "
                "border: 1px solid #2A2D33; border-radius: 3px; "
                "font-size: 9px; font-weight: 700;"
            )
            btn_logic.clicked.connect(
                lambda _=False, o=opt: self._on_toggle_logic(o)
            )
            header.addWidget(btn_logic)

        header_label = QLabel("Условия:" if has_conditions else "Условия:")
        header_label.setStyleSheet(
            "color: #5A5F68; font-size: 10px; font-weight: 600;"
        )
        header.addWidget(header_label)

        header.addStretch()

        btn_add = QPushButton("+ Добавить")
        btn_add.setFixedHeight(20)
        btn_add.setStyleSheet(
            "background: #202328; color: #858B93; "
            "border: 1px solid #2A2D33; border-radius: 3px; "
            "font-size: 9px; padding: 0 6px;"
        )
        btn_add.clicked.connect(
            lambda _=False, o=opt: self._on_add_condition(o)
        )
        header.addWidget(btn_add)

        v.addLayout(header)

        # --- Список условий ---
        if not has_conditions:
            empty = QLabel("  (нет условий \u2014 опция доступна всегда)")
            empty.setStyleSheet(
                "color: #5A5F68; font-size: 9px;"
            )
            v.addWidget(empty)
            return section

        for idx, c in enumerate(cond.items):
            v.addWidget(self._build_condition_row(opt, idx, c))

        return section

    def _build_condition_row(self, opt, idx, condition):
        """Одна строка условия."""
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)

        # Описание
        if condition.kind == "variable":
            desc = (
                f"{condition.target} "
                f"{condition.operator} "
                f"{condition.value}"
            )
        else:
            val = "true" if condition.value else "false"
            desc = f"{condition.target} {condition.operator} {val}"

        label = QLabel(desc)
        label.setStyleSheet(
            "color: #E5E5E5; font-size: 10px;"
        )
        h.addWidget(label, 1)

        # Edit
        btn_edit = QPushButton("\u270e")
        btn_edit.setFixedSize(20, 20)
        btn_edit.setToolTip("Редактировать")
        btn_edit.setStyleSheet(
            "background: transparent; color: #858B93; "
            "border: none; font-size: 11px;"
        )
        btn_edit.clicked.connect(
            lambda _=False, o=opt, i=idx: self._on_edit_condition(o, i)
        )
        h.addWidget(btn_edit)

        # Delete
        btn_del = QPushButton("\u00d7")
        btn_del.setFixedSize(20, 20)
        btn_del.setToolTip("Удалить")
        btn_del.setStyleSheet(
            "background: transparent; color: #858B93; "
            "border: none; font-size: 13px;"
        )
        btn_del.clicked.connect(
            lambda _=False, o=opt, i=idx: self._on_remove_condition(o, i)
        )
        h.addWidget(btn_del)

        return row

    # =========================================================
    # CONDITIONS HANDLERS
    # =========================================================

    def _clone_group(self, group):
        """Возвращает копию ConditionGroup (или новый пустой)."""
        if group is None:
            return ConditionGroup(logic="AND")
        # Восстанавливаем через to_dict → from_dict (безопасно)
        d = group.to_dict()
        if d is None:
            return ConditionGroup(logic=group.logic)
        new = ConditionGroup.from_dict(d)
        return new if new is not None else ConditionGroup(logic=group.logic)

    def _push_conditions(self, opt, new_group):
        """Пушит ChangePropertyCommand на opt.conditions."""
        old_group = opt.conditions
        cmd = ChangePropertyCommand(
            target=opt,
            prop_name="conditions",
            old_value=old_group,
            new_value=new_group,
            notify=lambda: self._refresh_current_option_ui(),
        )
        self._push(cmd)

    def _refresh_current_option_ui(self):
        """Полная перерисовка Inspector (для обновления UI option)."""
        if self.current_node_id:
            # Сохраняем фокус: перерисовываем через set_node
            self.set_node(self.current_node_id)

    def _on_add_condition(self, opt):
        dlg = ConditionDialog(
            project_data=self.project_data,
            condition=None,
            parent=self,
        )
        dlg.exec()

        if dlg.result_condition is None:
            return

        new_group = self._clone_group(opt.conditions)
        new_group.add(dlg.result_condition)
        self._push_conditions(opt, new_group)

    def _on_edit_condition(self, opt, idx):
        old_cond = opt.conditions.get(idx)
        if old_cond is None:
            return

        dlg = ConditionDialog(
            project_data=self.project_data,
            condition=old_cond,
            parent=self,
        )
        dlg.exec()

        if dlg.result_condition is None:
            return

        new_group = self._clone_group(opt.conditions)
        new_group.items[idx] = dlg.result_condition
        self._push_conditions(opt, new_group)

    def _on_remove_condition(self, opt, idx):
        new_group = self._clone_group(opt.conditions)
        new_group.remove(idx)
        self._push_conditions(opt, new_group)

    def _on_toggle_logic(self, opt):
        new_group = self._clone_group(opt.conditions)
        new_group.logic = "OR" if new_group.logic == "AND" else "AND"
        self._push_conditions(opt, new_group)

    # =========================================================
    # EFFECTS SECTION
    # =========================================================

    def _build_effects_section(self, opt):
        """Строит секцию Effects для одного option."""
        section = QWidget()
        v = QVBoxLayout(section)
        v.setContentsMargins(24, 0, 0, 0)
        v.setSpacing(3)

        has_effects = bool(opt.effects)

        # --- Заголовок ---
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(4)

        header_label = QLabel("Эффекты:")
        header_label.setStyleSheet(
            "color: #5A5F68; font-size: 10px; font-weight: 600;"
        )
        header.addWidget(header_label)
        header.addStretch()

        btn_add = QPushButton("+ Добавить")
        btn_add.setFixedHeight(20)
        btn_add.setStyleSheet(
            "background: #202328; color: #858B93; "
            "border: 1px solid #2A2D33; border-radius: 3px; "
            "font-size: 9px; padding: 0 6px;"
        )
        btn_add.clicked.connect(
            lambda _=False, o=opt: self._on_add_effect(o)
        )
        header.addWidget(btn_add)

        v.addLayout(header)

        # --- Список ---
        if not has_effects:
            empty = QLabel("  (нет эффектов \u2014 выбор ничего не изменит)")
            empty.setStyleSheet("color: #5A5F68; font-size: 9px;")
            v.addWidget(empty)
            return section

        for idx, e in enumerate(opt.effects):
            v.addWidget(self._build_effect_row(opt, idx, e))

        return section

    def _build_effect_row(self, opt, idx, effect):
        """Одна строка эффекта."""
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)

        # Описание
        if effect.kind == "variable":
            desc = (
                f"{effect.target} {effect.operation} "
                f"{effect.value}"
            )
        else:
            val = "true" if effect.value else "false"
            desc = f"{effect.target} {effect.operation} {val}"

        label = QLabel(desc)
        label.setStyleSheet("color: #E5E5E5; font-size: 10px;")
        h.addWidget(label, 1)

        # Edit
        btn_edit = QPushButton("\u270e")
        btn_edit.setFixedSize(20, 20)
        btn_edit.setToolTip("Редактировать")
        btn_edit.setStyleSheet(
            "background: transparent; color: #858B93; "
            "border: none; font-size: 11px;"
        )
        btn_edit.clicked.connect(
            lambda _=False, o=opt, i=idx: self._on_edit_effect(o, i)
        )
        h.addWidget(btn_edit)

        # Delete
        btn_del = QPushButton("\u00d7")
        btn_del.setFixedSize(20, 20)
        btn_del.setToolTip("Удалить")
        btn_del.setStyleSheet(
            "background: transparent; color: #858B93; "
            "border: none; font-size: 13px;"
        )
        btn_del.clicked.connect(
            lambda _=False, o=opt, i=idx: self._on_remove_effect(o, i)
        )
        h.addWidget(btn_del)

        return row

    # =========================================================
    # EFFECTS HANDLERS
    # =========================================================

    def _clone_effects(self, effects):
        """Возвращает новый list[Effect] из существующего."""
        if not effects:
            return []
        result = []
        for e in effects:
            d = e.to_dict()
            new_e = Effect.from_dict(d)
            if new_e is not None:
                result.append(new_e)
        return result

    def _push_effects(self, opt, new_effects):
        """Пушит ChangePropertyCommand на opt.effects."""
        old_effects = list(opt.effects) if opt.effects else []
        cmd = ChangePropertyCommand(
            target=opt,
            prop_name="effects",
            old_value=old_effects,
            new_value=new_effects,
            notify=lambda: self._refresh_current_option_ui(),
        )
        self._push(cmd)

    def _on_add_effect(self, opt):
        dlg = EffectDialog(
            project_data=self.project_data,
            effect=None,
            parent=self,
        )
        dlg.exec()

        if dlg.result_effect is None:
            return

        new_effects = self._clone_effects(opt.effects)
        new_effects.append(dlg.result_effect)
        self._push_effects(opt, new_effects)

    def _on_edit_effect(self, opt, idx):
        if idx < 0 or idx >= len(opt.effects):
            return

        old_effect = opt.effects[idx]

        dlg = EffectDialog(
            project_data=self.project_data,
            effect=old_effect,
            parent=self,
        )
        dlg.exec()

        if dlg.result_effect is None:
            return

        new_effects = self._clone_effects(opt.effects)
        new_effects[idx] = dlg.result_effect
        self._push_effects(opt, new_effects)

    def _on_remove_effect(self, opt, idx):
        if idx < 0 or idx >= len(opt.effects):
            return

        new_effects = self._clone_effects(opt.effects)
        new_effects.pop(idx)
        self._push_effects(opt, new_effects)

    def _show_placeholder(self):
        self._clear_content()
        label = QLabel("Выберите узел, чтобы редактировать его свойства.")
        label.setWordWrap(True)
        label.setStyleSheet("color: #888; padding: 20px 0;")
        self.content_layout.addWidget(label)
        self.content_layout.addStretch()

    # =========================================================
    # ПУБЛИЧНЫЙ API
    # =========================================================

    def set_dialogue(self, dialogue):
        self.dialogue = dialogue
        self.current_node_id = None
        self._show_placeholder()

    def clear(self):
        self.current_node_id = None
        self._show_placeholder()

    def set_project_data(self, project_data):
        """Устанавливает справочник проекта (characters, variables, flags)."""
        self.project_data = project_data

    def set_node(self, node_id):
        if self.dialogue is None:
            return

        node = self.dialogue.get_node(node_id)
        if node is None:
            self._show_placeholder()
            return

        self.current_node_id = node_id

        # Блокируем создание команд на время заполнения UI
        self._updating = True
        try:
            self._clear_content()

            if isinstance(node, StartNode):
                self._build_start_ui(node)
            elif isinstance(node, ReplyNode):
                self._build_reply_ui(node)
            elif isinstance(node, ChoiceNode):
                self._build_choice_ui(node)
            elif isinstance(node, EndNode):
                self._build_end_ui(node)
            else:
                label = QLabel(f"Неизвестный тип: {node.type}")
                self.content_layout.addWidget(label)

            self.content_layout.addStretch()
        finally:
            self._updating = False

    # =========================================================
    # START / END
    # =========================================================

    def _build_start_ui(self, node):
        label = QLabel("Начало диалога")
        label.setStyleSheet("font-weight: 600; padding: 8px 0;")
        self.content_layout.addWidget(label)

        hint = QLabel(
            "Точка входа в диалог.\n"
            "В диалоге может быть только один StartNode."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888;")
        self.content_layout.addWidget(hint)

    def _build_end_ui(self, node):
        label = QLabel("Конец диалога")
        label.setStyleSheet("font-weight: 600; padding: 8px 0;")
        self.content_layout.addWidget(label)

        hint = QLabel(
            "Точка завершения диалога.\n"
            "Узел не имеет исходящих связей."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888;")
        self.content_layout.addWidget(hint)

        # Read-only блок outcome (архитектурный контракт)
        self._add_outcome_block(node)

    # =========================================================
    # REPLY
    # =========================================================

    def _build_reply_ui(self, node):
        # === Персонаж ===
        self._build_speaker_widget(node)

        # === Текст реплики ===
        text_edit = QPlainTextEdit()
        text_edit.blockSignals(True)
        text_edit.setPlainText(node.text)
        text_edit.blockSignals(False)
        text_edit.setPlaceholderText("Текст реплики")
        text_edit.setMinimumHeight(120)

        def on_text_changed():
            if self._updating:
                return
            old = node.text
            new = text_edit.toPlainText()
            if old == new:
                return
            cmd = ChangePropertyCommand(
                target=node,
                prop_name="text",
                old_value=old,
                new_value=new,
                notify=lambda: self.node_changed.emit(node.id),
            )
            self._push(cmd)

        text_edit.textChanged.connect(on_text_changed)
        self._add_row("Текст реплики", text_edit)

        # Read-only блок (архитектурный контракт)
        self._add_presentation_block(node)

    def _build_speaker_widget(self, node):
        """Строит dropdown (или fallback QLineEdit) для выбора персонажа."""
        characters = []
        if self.project_data is not None:
            characters = sorted(
                self.project_data.characters.values(),
                key=lambda c: (c.name or c.id).lower(),
            )

        if not characters:
            # Нет справочника — fallback на QLineEdit
            speaker_edit = QLineEdit()
            speaker_edit.blockSignals(True)
            speaker_edit.setText(node.speaker_id or "")
            speaker_edit.blockSignals(False)
            speaker_edit.setPlaceholderText(
                "Введите имя персонажа (создастся slug)"
            )

            def on_speaker_changed(text):
                if self._updating:
                    return
                old = node.speaker_id or ""
                new_raw = text.strip()
                if not new_raw:
                    new = ""
                else:
                    # Slugify — как в модели
                    try:
                        from ..io.storage import _slugify
                        new = _slugify(new_raw)
                    except Exception:
                        new = new_raw
                if new == old:
                    return
                cmd = ChangePropertyCommand(
                    target=node,
                    prop_name="speaker_id",
                    old_value=old,
                    new_value=new,
                    notify=lambda: self.node_changed.emit(node.id),
                )
                self._push(cmd)

            speaker_edit.textChanged.connect(on_speaker_changed)
            self._add_row("Персонаж", speaker_edit)
            return

        # Есть справочник — QComboBox
        combo = QComboBox()
        combo.setEditable(False)

        # Пустой вариант
        combo.addItem("— не указан —", "")

        # Все персонажи
        current_idx = 0
        current_id = node.speaker_id or ""

        for char in characters:
            label = char.name or char.id
            combo.addItem(f"{label}  ({char.id})", char.id)
            if char.id == current_id:
                current_idx = combo.count() - 1

        # Если текущий speaker_id не найден в справочнике — добавим
        if current_id and current_idx == 0:
            combo.addItem(
                f"{current_id}  (нет в справочнике)",
                current_id,
            )
            current_idx = combo.count() - 1

        combo.blockSignals(True)
        combo.setCurrentIndex(current_idx)
        combo.blockSignals(False)

        def on_combo_changed(idx):
            if self._updating:
                return
            new_id = combo.itemData(idx) or ""
            old_id = node.speaker_id or ""
            if new_id == old_id:
                return
            cmd = ChangePropertyCommand(
                target=node,
                prop_name="speaker_id",
                old_value=old_id,
                new_value=new_id,
                notify=lambda: self.node_changed.emit(node.id),
            )
            self._push(cmd)

        combo.currentIndexChanged.connect(on_combo_changed)
        self._add_row("Персонаж", combo)

    # =========================================================
    # CHOICE
    # =========================================================

    def _build_choice_ui(self, node):
        # Question
        question_edit = QLineEdit()
        question_edit.blockSignals(True)
        question_edit.setText(node.question)
        question_edit.blockSignals(False)
        question_edit.setPlaceholderText("Вопрос или ремарка")

        def on_question_changed(text):
            if self._updating:
                return
            old = node.question
            if old == text:
                return
            cmd = ChangePropertyCommand(
                target=node,
                prop_name="question",
                old_value=old,
                new_value=text,
                notify=lambda: self.node_changed.emit(node.id),
            )
            self._push(cmd)

        question_edit.textChanged.connect(on_question_changed)
        self._add_row("Вопрос", question_edit)

        # Заголовок
        options_label = QLabel("Варианты ответа")
        options_label.setStyleSheet(
            "font-weight: 600; padding-top: 8px;"
        )
        self.content_layout.addWidget(options_label)

        # Контейнер
        self._options_container = QWidget()
        self._options_layout = QVBoxLayout(self._options_container)
        self._options_layout.setContentsMargins(0, 0, 0, 0)
        self._options_layout.setSpacing(4)

        self.content_layout.addWidget(self._options_container)

        # Кнопка «Добавить»
        add_btn = QPushButton("+ Добавить вариант")
        add_btn.clicked.connect(lambda: self._on_add_option(node))
        self.content_layout.addWidget(add_btn)

        # Заполняем
        self._rebuild_options(node)

    def _rebuild_options(self, node):
        while self._options_layout.count() > 0:
            item = self._options_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        node.sort_options()

        for idx, opt in enumerate(node.options):
            row = self._build_option_row(node, opt, idx)
            self._options_layout.addWidget(row)

            info = self._build_option_info(opt)
            self._options_layout.addWidget(info)

    def _build_option_row(self, node, opt, idx):
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)

        num = QLabel(f"{idx + 1}.")
        num.setFixedWidth(20)
        h.addWidget(num)

        edit = QLineEdit()
        edit.blockSignals(True)
        edit.setText(opt.text)
        edit.blockSignals(False)
        edit.setPlaceholderText("Текст варианта")

        def on_text_changed(text):
            if self._updating:
                return
            old = opt.text
            if old == text:
                return
            cmd = ChangePropertyCommand(
                target=opt,
                prop_name="text",
                old_value=old,
                new_value=text,
                notify=lambda: self.node_changed.emit(node.id),
            )
            self._push(cmd)

        edit.textChanged.connect(on_text_changed)
        h.addWidget(edit, 1)

        if idx > 0:
            up_btn = QPushButton("▲")
            up_btn.setFixedWidth(28)
            up_btn.clicked.connect(
                lambda _=False, i=idx: self._on_move_option(node, i, -1)
            )
            h.addWidget(up_btn)

        if idx < len(node.options) - 1:
            down_btn = QPushButton("▼")
            down_btn.setFixedWidth(28)
            down_btn.clicked.connect(
                lambda _=False, i=idx: self._on_move_option(node, i, +1)
            )
            h.addWidget(down_btn)

        del_btn = QPushButton("×")
        del_btn.setFixedWidth(28)
        del_btn.clicked.connect(
            lambda _=False, o=opt: self._on_delete_option(node, o)
        )
        h.addWidget(del_btn)

        return row

    def _on_add_option(self, node):
        if self._updating:
            return

        order = max((o.order for o in node.options), default=-1) + 1
        opt = ChoiceOption(
            option_id=generate_option_id(),
            text="Новый вариант",
            order=order,
        )

        cmd = AddOptionCommand(
            node=node,
            option=opt,
            notify=lambda: self._after_option_change(node),
        )
        self._push(cmd)

    def _on_delete_option(self, node, opt):
        if self._updating:
            return

        cmd = RemoveOptionCommand(
            node=node,
            option=opt,
            notify=lambda: self._after_option_change(node),
        )
        self._push(cmd)

    def _on_move_option(self, node, idx, delta):
        if self._updating:
            return

        node.sort_options()
        new_idx = idx + delta

        if new_idx < 0 or new_idx >= len(node.options):
            return

        a = node.options[idx]
        b = node.options[new_idx]

        cmd = MoveOptionCommand(
            node=node,
            option_a=a,
            option_b=b,
            notify=lambda: self.node_changed.emit(node.id),
        )
        self._push(cmd)

        # После смены порядка перестраиваем UI
        self._updating = True
        try:
            self._rebuild_options(node)
        finally:
            self._updating = False

    def _after_option_change(self, node):
        """После add/remove option — обновить визуал + порты + UI."""
        self.node_changed.emit(node.id)
        self.connections_changed.emit()

        # Перестраиваем UI (текущий узел — тот же)
        self._updating = True
        try:
            self._rebuild_options(node)
        finally:
            self._updating = False
