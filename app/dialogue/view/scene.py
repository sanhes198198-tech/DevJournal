"""
QGraphicsScene для редактора диалогов.

Собирает визуальные узлы (DialogueNodeItem) и связи
(DialogueConnectionItem) из модели Dialogue.

Отслеживает движение узлов и обновляет пути связей.
"""

from PySide6.QtCore import QRectF
from PySide6.QtWidgets import QGraphicsScene

from .node_item import DialogueNodeItem
from .connection_item import DialogueConnectionItem


class DialogueScene(QGraphicsScene):
    """Сцена редактора диалогов."""

    SCENE_PADDING = 5000.0

    def __init__(self, parent=None):
        super().__init__(parent)

        # Модель
        self.dialogue = None

        # Визуальные элементы
        self.node_items = {}         # dict[node_id, DialogueNodeItem]
        self.connection_items = {}   # dict[conn_id, DialogueConnectionItem]

        # Сцена большая — граф может быть большим
        self.setSceneRect(
            -self.SCENE_PADDING,
            -self.SCENE_PADDING,
            2 * self.SCENE_PADDING,
            2 * self.SCENE_PADDING,
        )

        self.setBackgroundBrush(self._bg_brush())

    # =========================================================
    # BACKGROUND
    # =========================================================

    def _bg_brush(self):
        from PySide6.QtGui import QColor, QBrush
        return QBrush(QColor("#FAFAF8"))

    # =========================================================
    # ПОСТРОЕНИЕ ИЗ МОДЕЛИ
    # =========================================================

    def rebuild_from_model(self, dialogue):
        """
        Полностью пересобирает сцену из модели.

        Удаляет все items и создаёт новые.
        """
        self.dialogue = dialogue

        # Очищаем
        self.clear()
        self.node_items.clear()
        self.connection_items.clear()

        if dialogue is None:
            return

        # 1. Узлы
        for model_node in dialogue.nodes.values():
            self._add_node_item(model_node)

        # 2. Связи (после узлов, чтобы порты уже существовали)
        for model_conn in dialogue.connections:
            self._add_connection_item(model_conn)

    # =========================================================
    # ДОБАВЛЕНИЕ УЗЛОВ
    # =========================================================

    def _add_node_item(self, model_node):
        """Создаёт DialogueNodeItem и добавляет в сцену."""
        item = DialogueNodeItem(model_node)
        self.addItem(item)
        self.node_items[model_node.id] = item
        return item

    def add_node_item(self, model_node):
        """Публичный метод — добавляет один узел."""
        if model_node.id in self.node_items:
            return self.node_items[model_node.id]
        return self._add_node_item(model_node)

    # =========================================================
    # ДОБАВЛЕНИЕ СВЯЗЕЙ
    # =========================================================

    def _add_connection_item(self, model_conn):
        """Создаёт DialogueConnectionItem и добавляет в сцену."""
        src_item = self.node_items.get(model_conn.source_node_id)
        tgt_item = self.node_items.get(model_conn.target_node_id)

        if src_item is None or tgt_item is None:
            # Некуда подключать — тихо пропускаем
            return None

        src_port = src_item.get_port(
            model_conn.source_port,
            is_input=False,
        )
        tgt_port = tgt_item.get_port(
            model_conn.target_port,
            is_input=True,
        )

        if src_port is None or tgt_port is None:
            # Порт не найден — тихо пропускаем
            return None

        item = DialogueConnectionItem(
            model_conn,
            src_port,
            tgt_port,
        )
        self.addItem(item)
        self.connection_items[model_conn.id] = item
        return item

    def add_connection_item(self, model_conn):
        """Публичный метод — добавляет одну связь."""
        if model_conn.id in self.connection_items:
            return self.connection_items[model_conn.id]
        return self._add_connection_item(model_conn)

    # =========================================================
    # ОБНОВЛЕНИЕ СВЯЗЕЙ ПРИ ДВИЖЕНИИ УЗЛОВ
    # =========================================================

    def on_node_moved(self, node_id):
        """
        Вызывается, когда узел переместился.

        Обновляет все связи, исходящие из узла или входящие в него.
        """
        if self.dialogue is None:
            return

        for model_conn in self.dialogue.connections:
            if (
                model_conn.source_node_id == node_id
                or model_conn.target_node_id == node_id
            ):
                conn_item = self.connection_items.get(model_conn.id)
                if conn_item is not None:
                    conn_item.update_path()

    # =========================================================
    # УДАЛЕНИЕ
    # =========================================================

    def remove_node_item(self, node_id):
        """Удаляет визуальный узел и все его связи."""
        node_item = self.node_items.pop(node_id, None)

        if node_item is None:
            return

        # Удаляем связанные connections
        conn_ids_to_remove = []

        for conn_id, conn_item in self.connection_items.items():
            mc = conn_item.model_connection
            if (
                mc.source_node_id == node_id
                or mc.target_node_id == node_id
            ):
                conn_ids_to_remove.append(conn_id)

        for conn_id in conn_ids_to_remove:
            conn_item = self.connection_items.pop(conn_id, None)
            if conn_item is not None:
                conn_item.detach_from_ports()
                self.removeItem(conn_item)

        # Удаляем сам узел
        self.removeItem(node_item)

    def remove_connection_item(self, connection_id):
        """Удаляет визуальную связь."""
        conn_item = self.connection_items.pop(connection_id, None)
        if conn_item is not None:
            conn_item.detach_from_ports()
            self.removeItem(conn_item)

    # =========================================================
    # ПОИСК
    # =========================================================

    def get_node_item(self, node_id):
        return self.node_items.get(node_id)

    def get_connection_item(self, connection_id):
        return self.connection_items.get(connection_id)

    def get_selected_node_items(self):
        """Все выделенные DialogueNodeItem."""
        result = []
        for item in self.selectedItems():
            if isinstance(item, DialogueNodeItem):
                result.append(item)
        return result

    def get_selected_connection_items(self):
        """Все выделенные DialogueConnectionItem."""
        result = []
        for item in self.selectedItems():
            if isinstance(item, DialogueConnectionItem):
                result.append(item)
        return result

    # =========================================================
    # СИНХРОНИЗАЦИЯ С МОДЕЛЬЮ
    # =========================================================

    def sync_positions_to_model(self):
        """
        Синхронизирует позиции визуальных узлов обратно в модель.

        Обычно не нужно — itemChange уже обновляет модель.
        Но полезно перед сохранением как подстраховка.
        """
        if self.dialogue is None:
            return

        for node_id, node_item in self.node_items.items():
            model_node = self.dialogue.get_node(node_id)
            if model_node is None:
                continue
            pos = node_item.pos()
            model_node.x = float(pos.x())
            model_node.y = float(pos.y())
