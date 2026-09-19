"""
Предпросмотр диалога — проигрывание как в игре.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class PreviewDialog(QDialog):
    """Окно предпросмотра диалога."""

    def __init__(self, dialogue, parent=None):
        super().__init__(parent)

        self.dialogue = dialogue
        self.current_node_id = None

        self.setWindowTitle("Предпросмотр диалога")
        self.resize(700, 500)

        self._apply_theme()

        self._build_ui()
        self._start()

    def _apply_theme(self):
        """Применяет тёмную тему к окну."""
        import os
        qss_path = os.path.join(
            os.path.dirname(__file__),
            "theme.qss",
        )
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                qss = f.read()
            self.setStyleSheet(qss)
        except Exception:
            pass

    def _build_ui(self):
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(0, 0, 0, 0)
        self.outer.setSpacing(0)

        top = QWidget()
        top.setStyleSheet(
            "background: #17191C; border-bottom: 1px solid #2A2D33;"
        )
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(16, 8, 16, 8)

        self.title_label = QLabel(
            "Предпросмотр: " + (self.dialogue.name or "Диалог")
        )
        self.title_label.setStyleSheet(
            "font-weight: 600; font-size: 13px; color: #E5E5E5;"
        )
        top_layout.addWidget(self.title_label)
        top_layout.addStretch()

        btn_restart = QPushButton("Сначала")
        btn_restart.setAutoDefault(False)
        btn_restart.setDefault(False)
        btn_restart.clicked.connect(self._start)
        top_layout.addWidget(btn_restart)

        self.outer.addWidget(top)

        center = QWidget()
        center.setStyleSheet("background: #111214;")

        self.center_layout = QVBoxLayout(center)
        self.center_layout.setContentsMargins(40, 30, 40, 30)
        self.center_layout.setSpacing(16)

        self.speaker_label = QLabel()
        self.speaker_label.setStyleSheet(
            "font-weight: 600; font-size: 14px; color: #4A90E2;"
        )
        self.speaker_label.setWordWrap(True)
        self.center_layout.addWidget(self.speaker_label)

        self.body_label = QLabel()
        self.body_label.setStyleSheet(
            "font-size: 14px; color: #E5E5E5;"
        )
        self.body_label.setWordWrap(True)
        self.center_layout.addWidget(self.body_label)

        self.center_layout.addStretch()

        self.actions_widget = QWidget()
        self.actions_layout = QVBoxLayout(self.actions_widget)
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(8)
        self.center_layout.addWidget(self.actions_widget)

        self.outer.addWidget(center, 1)

        bottom = QWidget()
        bottom.setStyleSheet(
            "background: #17191C; border-top: 1px solid #2A2D33;"
        )
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(16, 6, 16, 6)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(
            "color: #858B93; font-size: 11px;"
        )
        bottom_layout.addWidget(self.status_label)
        bottom_layout.addStretch()

        btn_close = QPushButton("Закрыть")
        btn_close.setAutoDefault(False)
        btn_close.setDefault(False)
        btn_close.clicked.connect(self.accept)
        bottom_layout.addWidget(btn_close)

        self.outer.addWidget(bottom)

    def _start(self):
        if self.dialogue is None:
            self._show_error("Диалог не загружен.")
            return

        starts = [
            n for n in self.dialogue.nodes.values()
            if n.type == "start"
        ]

        if not starts:
            self._show_error(
                "В диалоге нет START узла. "
                "Добавьте START и соедините с первой репликой."
            )
            return

        self._goto(starts[0].id)

    def _goto(self, node_id):
        self.current_node_id = node_id
        node = self.dialogue.get_node(node_id)

        if node is None:
            self._show_error(
                "Узел " + node_id[:8] + "... не найден."
            )
            return

        if node.type == "start":
            self._handle_start(node)
        elif node.type == "reply":
            self._handle_reply(node)
        elif node.type == "choice":
            self._handle_choice(node)
        elif node.type == "end":
            self._handle_end(node)
        else:
            self._show_error("Неизвестный тип: " + node.type)

    def _handle_start(self, node):
        self._advance_from(node.id, "output")

    def _handle_reply(self, node):
        self._clear_actions()

        speaker = getattr(node, "speaker", "") or "???"
        text = getattr(node, "text", "") or "(пустая реплика)"

        self.speaker_label.setStyleSheet(
            "font-weight: 600; font-size: 14px; color: #4A90E2;"
        )
        self.speaker_label.setText(speaker)

        self.body_label.setStyleSheet(
            "font-size: 14px; color: #E5E5E5;"
        )
        self.body_label.setText(text)

        btn = QPushButton("Далее  ->")
        btn.setAutoDefault(False)
        btn.setDefault(False)
        btn.setMinimumHeight(36)
        btn.setStyleSheet(
            "font-weight: 600; background: #4A90E2; "
            "color: white; border-radius: 4px; padding: 6px 20px;"
        )
        btn.clicked.connect(
            lambda: self._advance_from(node.id, "output")
        )
        self.actions_layout.addWidget(
            btn, alignment=Qt.AlignmentFlag.AlignRight
        )

        self._set_status("Узел: REPLY (" + node.id[:8] + ")")

    def _handle_choice(self, node):
        self._clear_actions()

        question = getattr(node, "question", "") or "(вопрос без текста)"
        options = getattr(node, "options", [])

        self.speaker_label.setStyleSheet(
            "font-weight: 600; font-size: 14px; color: #F5A623;"
        )
        self.speaker_label.setText("(выбор)")
        self.body_label.setText(question)

        if not options:
            self._show_error(
                "CHOICE без вариантов. Добавьте варианты в Inspector."
            )
            return

        sorted_options = sorted(options, key=lambda o: o.order)

        for opt in sorted_options:
            port = "opt_" + opt.id
            conn = self.dialogue.find_connection(node.id, port)
            is_dead = conn is None

            btn = QPushButton(opt.text or "(без текста)")
            btn.setMinimumHeight(40)
            btn.setStyleSheet(
                "text-align: left; padding: 10px 16px; font-size: 13px;"
                + ("color: #999;" if is_dead else "")
            )

            if is_dead:
                btn.setText(
                    (opt.text or "(без текста)") + "  -- НЕТ СВЯЗИ"
                )
                btn.setEnabled(False)
            else:
                btn.clicked.connect(
                    lambda _=False, p=port: self._advance_from(
                        node.id, p
                    )
                )

            self.actions_layout.addWidget(btn)

        self._set_status(
            "Узел: CHOICE (" + node.id[:8] + "), вариантов: "
            + str(len(options))
        )

    def _handle_end(self, node):
        self._clear_actions()

        self.speaker_label.setText("")
        self.body_label.setText("Конец диалога")

        outcome = getattr(node, "outcome", "end")
        target = getattr(node, "target_dialogue_id", None)

        if outcome == "dialogue" and target:
            hint = QLabel("-> Переход в диалог: " + target[:8] + "...")
            hint.setStyleSheet("color: #858B93; font-size: 12px;")
            self.actions_layout.addWidget(hint)
        else:
            hint = QLabel("(завершение)")
            hint.setStyleSheet("color: #858B93; font-size: 12px;")
            self.actions_layout.addWidget(hint)

        btn = QPushButton("Сначала")
        btn.setMinimumHeight(36)
        btn.clicked.connect(self._start)
        self.actions_layout.addWidget(
            btn, alignment=Qt.AlignmentFlag.AlignRight
        )

        self._set_status("Узел: END (" + node.id[:8] + ")")

    def _advance_from(self, node_id, port):
        conn = self.dialogue.find_connection(node_id, port)

        if conn is None:
            self._show_error(
                "Нет исходящей связи от узла "
                + node_id[:8]
                + " (порт " + port + "). Это тупик."
            )
            return

        self._goto(conn.target_node_id)

    def _clear_actions(self):
        while self.actions_layout.count() > 0:
            item = self.actions_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _show_error(self, message):
        self._clear_actions()

        self.speaker_label.setStyleSheet(
            "font-weight: 600; font-size: 14px; color: #D0021B;"
        )
        self.speaker_label.setText("[ОШИБКА ПРЕДПРОСМОТРА]")

        self.body_label.setStyleSheet(
            "font-size: 13px; color: #E5E5E5;"
        )
        self.body_label.setText(message)

        btn = QPushButton("Сначала")
        btn.clicked.connect(self._start)
        self.actions_layout.addWidget(btn)

        self._set_status("Ошибка предпросмотра")

    def _set_status(self, text):
        self.status_label.setText(text)