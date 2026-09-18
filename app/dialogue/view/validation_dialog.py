"""
Диалог валидации диалога — список проблем с навигацией.

Клик по проблеме → центрировать view на проблемном узле.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QPushButton,
    QFrame,
)

from ..validation import LEVEL_ERROR, LEVEL_WARNING


class ValidationDialog(QDialog):
    """Диалог списка проблем валидации с навигацией."""

    def __init__(self, result, node_labels, parent=None):
        """
        Параметры:
            result — ValidationResult
            node_labels — dict[node_id, str] — отображаемые имена узлов
            parent — родительское окно
        """
        super().__init__(parent)

        self.result = result
        self.node_labels = node_labels or {}

        # Куда вернуть выбранный node_id
        self.selected_node_id = None

        self.setWindowTitle("Проверка диалога")
        self.resize(560, 420)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        errors = self.result.errors()
        warnings = self.result.warnings()

        # Заголовок со сводкой
        summary_text = (
            f"Ошибки: {len(errors)} · "
            f"Предупреждения: {len(warnings)}"
        )
        summary = QLabel(summary_text)
        summary.setStyleSheet(
            "font-weight: 600; font-size: 13px;"
        )
        layout.addWidget(summary)

        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # Список проблем
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(
            self._on_item_double_clicked
        )
        layout.addWidget(self.list_widget, 1)

        # Заполняем — сначала ошибки, потом предупреждения
        for issue in errors:
            self._add_issue(issue, is_error=True)

        for issue in warnings:
            self._add_issue(issue, is_error=False)

        if not errors and not warnings:
            item = QListWidgetItem("✓  Проблем не обнаружено")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.list_widget.addItem(item)

        # Кнопки внизу
        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)

        hint = QLabel(
            "Двойной клик — центрировать узел"
        )
        hint.setStyleSheet("color: #888; font-size: 10px;")
        buttons.addWidget(hint)

        buttons.addStretch()

        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        buttons.addWidget(btn_close)

        layout.addLayout(buttons)

    def _add_issue(self, issue, is_error):
        """Добавляет одну строку проблемы."""
        if is_error:
            prefix = "[ОШИБКА]"
            color = "#D0021B"
        else:
            prefix = "[!]"
            color = "#F5A623"

        # Метка узла (если есть)
        node_id = getattr(issue, "node_id", None)
        label_suffix = ""

        if node_id:
            display_name = self.node_labels.get(
                node_id, f"{node_id[:8]}…"
            )
            label_suffix = f" — {display_name}"

        text = f"{prefix} {issue.code}: {issue.message}{label_suffix}"

        item = QListWidgetItem(text)
        item.setForeground(_qcolor(color))

        # Сохраняем node_id в UserRole
        item.setData(Qt.ItemDataRole.UserRole, node_id)

        # Если нет узла — не делаем «выделяемым для навигации»,
        # но курсор остаётся обычным
        if not node_id:
            item.setToolTip("У проблемы нет привязанного узла")

        self.list_widget.addItem(item)

    def _on_item_double_clicked(self, item):
        """Двойной клик → выбрать узел и закрыть диалог."""
        node_id = item.data(Qt.ItemDataRole.UserRole)
        if not node_id:
            return

        self.selected_node_id = node_id
        self.accept()


def _qcolor(hex_str):
    """Хелпер — превращает hex в QColor."""
    from PySide6.QtGui import QColor
    return QColor(hex_str)
