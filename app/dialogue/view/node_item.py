"""
Визуальный узел диалога.

QGraphicsItem, который отображает модель DialogueNode.
Содержит PortItem-ы (вход/выход).
Поддерживает перетаскивание.

После завершения drag — обновляет позицию в модели (x, y).
"""

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QColor,
    QPen,
    QBrush,
    QPainter,
    QFont,
    QFontMetrics,
)
from PySide6.QtWidgets import QGraphicsItem

from .port_item import PortItem


# =========================================================
# СТИЛЬ
# =========================================================

NODE_WIDTH = 260.0
NODE_HEADER_HEIGHT = 26.0
NODE_BODY_MIN_HEIGHT = 80.0

BORDER_WIDTH = 1.0
BORDER_RADIUS = 6.0
PORT_MARGIN = 14.0
CONTENT_PADDING = 10.0

COLOR_BG = QColor("#FFFFFF")
COLOR_HEADER = QColor("#F0F0F0")
COLOR_BORDER = QColor("#B0B0B0")
COLOR_BORDER_SELECTED = QColor("#4F7CFF")
COLOR_TEXT = QColor("#202020")
COLOR_TEXT_DIM = QColor("#808080")

# Цвета заголовков по типу узла
HEADER_COLORS = {
    "start": QColor("#7ED321"),
    "reply": QColor("#4A90E2"),
    "choice": QColor("#F5A623"),
    "end": QColor("#D0021B"),
}


# =========================================================
# УЗЕЛ
# =========================================================

class DialogueNodeItem(QGraphicsItem):
    """Визуальный узел диалога."""

    def __init__(self, model_node, parent=None):
        super().__init__(parent)

        self.model_node = model_node
        self.node_id = model_node.id
        self.node_type = model_node.type

        # Размеры (высота будет уточнена в _recalc_height)
        self._width = NODE_WIDTH
        self._height = NODE_HEADER_HEIGHT + NODE_BODY_MIN_HEIGHT

        # Порт: dict[port_name, PortItem]
        self.input_ports = {}
        self.output_ports = {}

        # Флаги — movable, selectable
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
            True,
        )
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
            True,
        )
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges,
            True,
        )

        self.setAcceptHoverEvents(True)

        # Позиция
        self.setPos(model_node.x, model_node.y)

        # Запоминаем позицию в начале drag — для MoveNodeCommand
        self._drag_start_pos = None

        # Пересчитываем высоту по содержимому ДО создания портов
        self._recalc_height()

        # Создаём порты
        self._build_ports()

    # =========================================================
    # СОЗДАНИЕ ПОРТОВ
    # =========================================================

    def _build_ports(self):
        """Создаёт PortItem-ы для всех портов модели."""

        input_names = self.model_node.get_input_ports()
        output_names = self.model_node.get_output_ports()

        input_count = len(input_names)
        output_count = len(output_names)

        # Входы — слева
        for idx, name in enumerate(input_names):
            port = PortItem(
                node_id=self.node_id,
                port_name=name,
                is_input=True,
                parent=self,
            )
            y = self._port_y(idx, input_count)
            port.setPos(0.0, y)
            self.input_ports[name] = port

        # Выходы — справа
        for idx, name in enumerate(output_names):
            port = PortItem(
                node_id=self.node_id,
                port_name=name,
                is_input=False,
                parent=self,
            )
            y = self._port_y(idx, output_count)
            port.setPos(self._width, y)
            self.output_ports[name] = port

    def _port_y(self, index, total):
        """Y-координата порта внутри узла."""
        if total == 0:
            return NODE_HEADER_HEIGHT

        # Равномерно по высоте ниже заголовка
        body_top = NODE_HEADER_HEIGHT
        body_height = self._height - body_top

        if total == 1:
            return body_top + body_height / 2

        step = body_height / (total + 1)
        return body_top + step * (index + 1)

    # =========================================================
    # ГЕОМЕТРИЯ
    # =========================================================

    def boundingRect(self):
        return QRectF(
            -2.0,
            -2.0,
            self._width + 4.0,
            self._height + 4.0,
        )

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        rect = QRectF(0, 0, self._width, self._height)

        # Тело узла
        painter.setBrush(QBrush(COLOR_BG))

        if self.isSelected():
            border_color = COLOR_BORDER_SELECTED
            border_width = 2.0
        else:
            border_color = COLOR_BORDER
            border_width = BORDER_WIDTH

        painter.setPen(QPen(border_color, border_width))
        painter.drawRoundedRect(rect, BORDER_RADIUS, BORDER_RADIUS)

        # Заголовок
        header_rect = QRectF(
            0,
            0,
            self._width,
            NODE_HEADER_HEIGHT,
        )

        header_color = HEADER_COLORS.get(self.node_type, COLOR_HEADER)

        painter.setBrush(QBrush(header_color))
        painter.setPen(Qt.PenStyle.NoPen)

        # Рисуем заголовок с закруглением сверху
        painter.drawRoundedRect(
            header_rect,
            BORDER_RADIUS,
            BORDER_RADIUS,
        )

        # Прямоугольник, чтобы закрыть нижние закругления заголовка
        painter.drawRect(
            QRectF(
                0,
                NODE_HEADER_HEIGHT / 2,
                self._width,
                NODE_HEADER_HEIGHT / 2,
            )
        )

        # Текст заголовка
        header_text = self._header_text()
        painter.setPen(QPen(QColor("#FFFFFF")))
        font = QFont()
        font.setBold(True)
        font.setPointSize(9)
        painter.setFont(font)

        painter.drawText(
            header_rect.adjusted(10, 0, -10, 0),
            Qt.AlignmentFlag.AlignVCenter
            | Qt.AlignmentFlag.AlignLeft,
            header_text,
        )

        # Текст тела
        body_text = self._body_text()
        if body_text:
            body_rect = QRectF(
                CONTENT_PADDING,
                NODE_HEADER_HEIGHT + CONTENT_PADDING,
                self._width - 2 * CONTENT_PADDING,
                self._height
                - NODE_HEADER_HEIGHT
                - 2 * CONTENT_PADDING,
            )

            painter.setPen(QPen(COLOR_TEXT))
            body_font = QFont()
            body_font.setPointSize(9)
            painter.setFont(body_font)

            painter.drawText(
                body_rect,
                Qt.AlignmentFlag.AlignTop
                | Qt.AlignmentFlag.AlignLeft
                | Qt.TextFlag.TextWordWrap,
                body_text,
            )

    # =========================================================
    # ТЕКСТЫ
    # =========================================================

    def _header_text(self):
        """Текст в заголовке узла."""
        type_label = {
            "start": "START",
            "reply": "REPLY",
            "choice": "CHOICE",
            "end": "END",
        }.get(self.node_type, self.node_type.upper())

        # Для reply — добавляем имя персонажа
        if self.node_type == "reply":
            speaker = getattr(self.model_node, "speaker", "")
            if speaker:
                return f"{type_label}  —  {speaker}"

        return type_label

    def _body_text(self):
        """Текст в теле узла."""
        if self.node_type == "reply":
            text = getattr(self.model_node, "text", "")
            return text or "(пустая реплика)"

        if self.node_type == "choice":
            question = getattr(self.model_node, "question", "")
            options = getattr(self.model_node, "options", [])
            lines = [question or "(без вопроса)", ""]
            for i, opt in enumerate(options):
                lines.append(f"{i + 1}. {opt.text}")
            return "\n".join(lines)

        if self.node_type == "start":
            return "Начало диалога"

        if self.node_type == "end":
            return "Конец диалога"

        return ""

    # =========================================================
    # ITEMCHANGE — обновление модели после перетаскивания
    # =========================================================

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # ВАЖНО: модель НЕ трогаем.
            # Позиция пишется в модель только при mouseRelease
            # через MoveNodeCommand — иначе undo не работает.

            # Обновляем пути связей во время движения —
            # чтобы кривые «тянулись» за узлом.
            scene = self.scene()
            if scene is not None:
                on_moved = getattr(scene, "on_node_moved", None)
                if callable(on_moved):
                    try:
                        on_moved(self.node_id)
                    except Exception:
                        pass

        return super().itemChange(change, value)

    # =========================================================
    # DRAG — MOVE (через команду)
    # =========================================================

    def mousePressEvent(self, event):
        # Запоминаем позицию ДО начала движения
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = self.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._drag_start_pos is None:
            return

        old_pos = self._drag_start_pos
        new_pos = self.pos()
        self._drag_start_pos = None

        # Не двигали — ничего не пушим
        if old_pos == new_pos:
            return

        scene = self.scene()
        if scene is None:
            return

        push = getattr(scene, "push_move_command", None)
        if callable(push):
            push(self, old_pos, new_pos)

    # =========================================================
    # УТИЛИТЫ
    # =========================================================

    def get_port(self, port_name, is_input):
        """Возвращает PortItem по имени и типу."""
        if is_input:
            return self.input_ports.get(port_name)
        return self.output_ports.get(port_name)

    def get_all_ports(self):
        """Все порты (вход + выход) как плоский список."""
        return list(self.input_ports.values()) + list(
            self.output_ports.values()
        )

    def refresh_text_only(self):
        """
        Лёгкое обновление — только пересчёт высоты и перерисовка.

        НЕ трогает порты — для случаев изменения текста/вопроса.
        """
        self._recalc_height()
        self.update()

    def refresh_from_model(self):
        """
        Обновляет визуал после изменения модели.

        Для MVP — пересоздаём порты и перерисовываем.
        """
        # Удаляем старые порты
        for port in self.get_all_ports():
            port.setParentItem(None)
            if port.scene() is not None:
                port.scene().removeItem(port)

        self.input_ports.clear()
        self.output_ports.clear()

        # Пересчитываем высоту
        self._recalc_height()

        # Пересоздаём порты
        self._build_ports()
        self.update()

    def _recalc_height(self):
        """Пересчитывает высоту узла."""
        body_text = self._body_text()
        lines = body_text.count("\n") + 1 if body_text else 1

        font = QFont()
        font.setPointSize(9)
        fm = QFontMetrics(font)

        line_height = fm.lineSpacing()
        needed = (
            NODE_HEADER_HEIGHT
            + 2 * CONTENT_PADDING
            + line_height * max(lines, 3)
        )

        self._height = max(needed, NODE_HEADER_HEIGHT + NODE_BODY_MIN_HEIGHT)

    def __repr__(self):
        return f"<DialogueNodeItem id={self.node_id!r} type={self.node_type!r}>"
