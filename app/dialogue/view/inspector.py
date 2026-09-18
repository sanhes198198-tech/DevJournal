"""
Инспектор свойств выбранного узла.

Правая панель редактора диалогов.
Меняется в зависимости от типа узла:
- StartNode    → только подпись
- ReplyNode    → speaker + text
- ChoiceNode   → question + список options
- EndNode      → только подпись

При изменении поля:
1. Мутируем модель (node.speaker = ...)
2. Испускаем сигнал node_changed → сцена перерисует узел
3. Если изменились порты (добавили/удалили option) →
   испускаем connections_changed → сцена перестроит связи
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
    QSizePolicy,
)

from ..model import (
    StartNode,
    ReplyNode,
    ChoiceNode,
    EndNode,
)


# =========================================================
# ИНСПЕКТОР
# =========================================================

class DialogueInspector(QWidget):
    """Правая панель редактирования свойств узла."""

    # Сигнал: модель узла изменилась (нужно обновить visual)
    node_changed = Signal(str)

    # Сигнал: изменились порты (нужно перестроить connections)
    connections_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.dialogue = None
        self.current_node_id = None

        # Чтобы при обновлении UI не было цикла сигналов
        self._updating = False

        self._build_ui()

    # =========================================================
    # UI КАРКАС
    # =========================================================

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(6)

        # Заголовок
        self.title_label = QLabel("Свойства")
        self.title_label.setStyleSheet(
            "font-weight: 600; font-size: 13px;"
        )

        outer.addWidget(self.title_label)

        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        outer.addWidget(line)

        # Область контента (прокручиваемая)
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

        # Изначально — пусто
        self._show_placeholder()

    def _clear_content(self):
        """Удаляет все виджеты из content."""
        while self.content_layout.count() > 0:
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _add_row(self, label_text, widget):
        """Добавляет строку 'label + widget'."""
        label = QLabel(label_text)
        label.setStyleSheet("color: #666; font-size: 11px;")

        self.content_layout.addWidget(label)
        self.content_layout.addWidget(widget)

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
        """Устанавливает модель диалога."""
        self.dialogue = dialogue
        self.current_node_id = None
        self._show_placeholder()

    def clear(self):
        """
        Сбрасывает инспектор — снимает выделение,
        но НЕ теряет ссылку на dialogue.
        """
        self.current_node_id = None
        self._show_placeholder()

    def set_node(self, node_id):
        """Показывает свойства узла."""
        if self.dialogue is None:
            return

        node = self.dialogue.get_node(node_id)
        if node is None:
            self._show_placeholder()
            return

        self.current_node_id = node_id

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

    # =========================================================
    # START
    # =========================================================

    def _build_start_ui(self, node):
        label = QLabel("Начало диалога")
        label.setStyleSheet(
            "font-weight: 600; padding: 8px 0;"
        )
        self.content_layout.addWidget(label)

        hint = QLabel(
            "Точка входа в диалог.\n"
            "В диалоге может быть только один StartNode."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888;")
        self.content_layout.addWidget(hint)

    # =========================================================
    # REPLY
    # =========================================================

    def _build_reply_ui(self, node):
        # Speaker
        speaker_edit = QLineEdit()
        speaker_edit.setText(node.speaker)
        speaker_edit.setPlaceholderText("Имя персонажа")

        def on_speaker_changed(text):
            if self._updating:
                return
            node.speaker = text
            self.node_changed.emit(node.id)

        speaker_edit.textChanged.connect(on_speaker_changed)
        self._add_row("Персонаж", speaker_edit)

        # Text
        text_edit = QPlainTextEdit()
        text_edit.setPlainText(node.text)
        text_edit.setPlaceholderText("Текст реплики")
        text_edit.setMinimumHeight(120)

        def on_text_changed():
            if self._updating:
                return
            node.text = text_edit.toPlainText()
            self.node_changed.emit(node.id)

        text_edit.textChanged.connect(on_text_changed)
        self._add_row("Текст реплики", text_edit)

    # =========================================================
    # CHOICE
    # =========================================================

    def _build_choice_ui(self, node):
        # Question
        question_edit = QLineEdit()
        question_edit.setText(node.question)
        question_edit.setPlaceholderText("Вопрос или ремарка")

        def on_question_changed(text):
            if self._updating:
                return
            node.question = text
            self.node_changed.emit(node.id)

        question_edit.textChanged.connect(on_question_changed)
        self._add_row("Вопрос", question_edit)

        # Заголовок списка options
        options_label = QLabel("Варианты ответа")
        options_label.setStyleSheet(
            "font-weight: 600; padding-top: 8px;"
        )
        self.content_layout.addWidget(options_label)

        # Контейнер для options
        self._options_container = QWidget()
        self._options_layout = QVBoxLayout(self._options_container)
        self._options_layout.setContentsMargins(0, 0, 0, 0)
        self._options_layout.setSpacing(4)

        self.content_layout.addWidget(self._options_container)

        # Кнопка «Добавить»
        add_btn = QPushButton("+ Добавить вариант")
        add_btn.clicked.connect(lambda: self._on_add_option(node))
        self.content_layout.addWidget(add_btn)

        # Заполняем список
        self._rebuild_options(node)

    def _rebuild_options(self, node):
        """Полностью перестраивает список вариантов."""
        # Очищаем контейнер
        while self._options_layout.count() > 0:
            item = self._options_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        node.sort_options()

        for idx, opt in enumerate(node.options):
            row = self._build_option_row(node, opt, idx)
            self._options_layout.addWidget(row)

    def _build_option_row(self, node, opt, idx):
        """Строка одного варианта."""
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)

        # Номер
        num = QLabel(f"{idx + 1}.")
        num.setFixedWidth(20)
        h.addWidget(num)

        # Текст
        edit = QLineEdit()
        edit.setText(opt.text)
        edit.setPlaceholderText("Текст варианта")

        def on_text_changed(text):
            if self._updating:
                return
            opt.text = text
            self.node_changed.emit(node.id)

        edit.textChanged.connect(on_text_changed)
        h.addWidget(edit, 1)

        # Вверх
        if idx > 0:
            up_btn = QPushButton("▲")
            up_btn.setFixedWidth(28)
            up_btn.clicked.connect(
                lambda _=False, i=idx: self._on_move_option(node, i, -1)
            )
            h.addWidget(up_btn)

        # Вниз
        if idx < len(node.options) - 1:
            down_btn = QPushButton("▼")
            down_btn.setFixedWidth(28)
            down_btn.clicked.connect(
                lambda _=False, i=idx: self._on_move_option(node, i, +1)
            )
            h.addWidget(down_btn)

        # Удалить
        del_btn = QPushButton("×")
        del_btn.setFixedWidth(28)
        del_btn.clicked.connect(
            lambda _=False, o=opt: self._on_delete_option(node, o)
        )
        h.addWidget(del_btn)

        return row

    def _on_add_option(self, node):
        node.add_option("Новый вариант")
        self._rebuild_options(node)

        # Порты изменились
        self.node_changed.emit(node.id)
        self.connections_changed.emit()

    def _on_delete_option(self, node, opt):
        node.remove_option(opt.id)
        self._rebuild_options(node)

        self.node_changed.emit(node.id)
        self.connections_changed.emit()

    def _on_move_option(self, node, idx, delta):
        node.sort_options()
        new_idx = idx + delta

        if new_idx < 0 or new_idx >= len(node.options):
            return

        a = node.options[idx]
        b = node.options[new_idx]

        a.order, b.order = b.order, a.order

        node.sort_options()
        self._rebuild_options(node)

        self.node_changed.emit(node.id)

    # =========================================================
    # END
    # =========================================================

    def _build_end_ui(self, node):
        label = QLabel("Конец диалога")
        label.setStyleSheet(
            "font-weight: 600; padding: 8px 0;"
        )
        self.content_layout.addWidget(label)

        hint = QLabel(
            "Точка завершения диалога.\n"
            "Узел не имеет исходящих связей."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888;")
        self.content_layout.addWidget(hint)
