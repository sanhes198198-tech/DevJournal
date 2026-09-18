"""
QGraphicsScene для редактора диалогов.

Собирает визуальные узлы (DialogueNodeItem) и связи
(DialogueConnectionItem) из модели Dialogue.

Отслеживает движение узлов и обновляет пути связей.
"""

from PySide6.QtCore import QRectF
from PySide6.QtWidgets import QGraphicsScene, QMenu

from .node_item import DialogueNodeItem
from .connection_item import DialogueConnectionItem
from .port_item import PortItem

from ..commands import CreateNodeCommand, DeleteNodeCommand, DeleteConnectionCommand
from ..ids import generate_node_id
from ..model import StartNode, ReplyNode, ChoiceNode, EndNode


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

        # Command sink — callable(command) или None
        self._command_sink = None

        # Сцена большая — граф может быть большим
        self.setSceneRect(
            -self.SCENE_PADDING,
            -self.SCENE_PADDING,
            2 * self.SCENE_PADDING,
            2 * self.SCENE_PADDING,
        )

        self.setBackgroundBrush(self._bg_brush())

    # =========================================================
    # COMMAND SINK
    # =========================================================

    def set_command_sink(self, sink):
        """sink — callable(command) или None."""
        self._command_sink = sink

    def _push(self, command):
        if self._command_sink is not None:
            self._command_sink(command)
        else:
            command.redo()

    # =========================================================
    # СОЗДАНИЕ УЗЛА (через команду)
    # =========================================================

    def _sync_node_visual(self, node):
        """Синхронизирует visual узла с моделью (add/remove)."""
        if self.dialogue is None:
            return

        in_model = node.id in self.dialogue.nodes
        in_scene = node.id in self.node_items

        if in_model and not in_scene:
            self.add_node_item(node)
        elif not in_model and in_scene:
            self.remove_node_item(node.id)

    def _create_node_at(self, node_type, scene_pos):
        """Создаёт узел заданного типа в точке сцены."""
        if self.dialogue is None:
            return None

        node_id = generate_node_id()
        x = float(scene_pos.x())
        y = float(scene_pos.y())

        if node_type == "start":
            node = StartNode(node_id, x=x, y=y)
        elif node_type == "reply":
            node = ReplyNode(node_id, x=x, y=y)
        elif node_type == "choice":
            node = ChoiceNode(node_id, x=x, y=y)
        elif node_type == "end":
            node = EndNode(node_id, x=x, y=y)
        else:
            return None

        def _notify():
            self._sync_node_visual(node)

        cmd = CreateNodeCommand(
            dialogue=self.dialogue,
            node=node,
            notify=_notify,
        )
        self._push(cmd)

        return node

    # =========================================================
    # ПОИСК ITEM'ОВ В ТОЧКЕ
    # =========================================================

    def _find_node_item_at(self, scene_pos):
        """Находит DialogueNodeItem в точке (учитывая родителя порта)."""
        for item in self.items(scene_pos):
            if isinstance(item, DialogueNodeItem):
                return item

            parent = item.parentItem()
            while parent is not None:
                if isinstance(parent, DialogueNodeItem):
                    return parent
                parent = parent.parentItem()

        return None

    def _find_connection_item_at(self, scene_pos):
        """Находит DialogueConnectionItem в точке."""
        for item in self.items(scene_pos):
            if isinstance(item, DialogueConnectionItem):
                return item
        return None

    # =========================================================
    # СИНХРОНИЗАЦИЯ VISUAL ↔ MODEL
    # =========================================================

    def _sync_connection_visual(self, connection):
        """Добавляет/удаляет visual связи по состоянию модели."""
        if self.dialogue is None:
            return

        in_model = any(
            c.id == connection.id
            for c in self.dialogue.connections
        )
        in_scene = connection.id in self.connection_items

        if in_model and not in_scene:
            self._add_connection_item(connection)
        elif not in_model and in_scene:
            self.remove_connection_item(connection.id)

    # =========================================================
    # УДАЛЕНИЕ (через команды)
    # =========================================================

    def _delete_node(self, node_id):
        """Удаляет узел + все его связи через DeleteNodeCommand."""
        if self.dialogue is None:
            return

        node = self.dialogue.get_node(node_id)
        if node is None:
            return

        related_connections = [
            c for c in self.dialogue.connections
            if c.source_node_id == node_id
            or c.target_node_id == node_id
        ]

        def _notify():
            self._sync_node_visual(node)
            for c in related_connections:
                self._sync_connection_visual(c)

        cmd = DeleteNodeCommand(
            dialogue=self.dialogue,
            node=node,
            notify=_notify,
        )
        self._push(cmd)

    def _delete_connection(self, connection_id):
        """Удаляет связь через DeleteConnectionCommand."""
        if self.dialogue is None:
            return

        conn = self.dialogue.get_connection(connection_id)
        if conn is None:
            return

        def _notify():
            self._sync_connection_visual(conn)

        cmd = DeleteConnectionCommand(
            dialogue=self.dialogue,
            connection=conn,
            notify=_notify,
        )
        self._push(cmd)

    def delete_selected(self):
        """Удаляет всё выделенное: сначала связи, потом узлы."""
        if self.dialogue is None:
            return

        selected_nodes = []
        selected_conns = []

        for item in self.selectedItems():
            if isinstance(item, DialogueNodeItem):
                selected_nodes.append(item.node_id)
            elif isinstance(item, DialogueConnectionItem):
                selected_conns.append(item.connection_id)

        for conn_id in selected_conns:
            self._delete_connection(conn_id)

        for node_id in selected_nodes:
            self._delete_node(node_id)

    # =========================================================
    # СОЗДАНИЕ РЯДОМ
    # =========================================================

    def _create_node_near(self, node_type, base_pos):
        """Создаёт узел со смещением вправо от базовой позиции."""
        from PySide6.QtCore import QPointF

        new_pos = QPointF(
            base_pos.x() + 320.0,
            base_pos.y(),
        )
        return self._create_node_at(node_type, new_pos)

    # =========================================================
    # CONTEXT MENU
    # =========================================================

    def _is_on_node(self, scene_pos):
        """True, если точка попадает в узел (или его потомка)."""
        for item in self.items(scene_pos):
            if isinstance(item, DialogueNodeItem):
                return True

            parent = item.parentItem()
            while parent is not None:
                if isinstance(parent, DialogueNodeItem):
                    return True
                parent = parent.parentItem()

        return False

    def contextMenuEvent(self, event):
        if self.dialogue is None:
            return

        scene_pos = event.scenePos()

        node_item = self._find_node_item_at(scene_pos)
        conn_item = self._find_connection_item_at(scene_pos)

        menu = QMenu()

        # --- ПКМ по узлу ---
        if node_item is not None:
            node = self.dialogue.get_node(node_item.node_id)
            if node is None:
                return

            act_delete = menu.addAction(
                f"Удалить узел ({node.type})"
            )
            menu.addSeparator()

            create_menu = menu.addMenu("Создать рядом")
            act_start = create_menu.addAction("START")
            act_reply = create_menu.addAction("REPLY")
            act_choice = create_menu.addAction("CHOICE")
            act_end = create_menu.addAction("END")

            chosen = menu.exec(event.screenPos())
            if chosen is None:
                return

            if chosen == act_delete:
                self._delete_node(node_item.node_id)
            elif chosen == act_start:
                self._create_node_near("start", node_item.pos())
            elif chosen == act_reply:
                self._create_node_near("reply", node_item.pos())
            elif chosen == act_choice:
                self._create_node_near("choice", node_item.pos())
            elif chosen == act_end:
                self._create_node_near("end", node_item.pos())

            event.accept()
            return

        # --- ПКМ по связи ---
        if conn_item is not None:
            act_delete = menu.addAction("Удалить связь")

            chosen = menu.exec(event.screenPos())
            if chosen == act_delete:
                self._delete_connection(conn_item.connection_id)

            event.accept()
            return

        # --- ПКМ по пустому ---
        act_start = menu.addAction("Создать START")
        act_reply = menu.addAction("Создать REPLY")
        act_choice = menu.addAction("Создать CHOICE")
        act_end = menu.addAction("Создать END")

        chosen = menu.exec(event.screenPos())
        if chosen is None:
            return

        if chosen == act_start:
            self._create_node_at("start", scene_pos)
        elif chosen == act_reply:
            self._create_node_at("reply", scene_pos)
        elif chosen == act_choice:
            self._create_node_at("choice", scene_pos)
        elif chosen == act_end:
            self._create_node_at("end", scene_pos)

        event.accept()

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

        Удаляет items вручную (без scene.clear()) — это безопаснее,
        потому что сохраняет нормальное состояние сцены.
        """
        self.dialogue = dialogue

        # 1. Удаляем connections — сначала отвязываем от портов
        for conn_item in list(self.connection_items.values()):
            try:
                conn_item.detach_from_ports()
            except Exception:
                pass
            try:
                if conn_item.scene() is self:
                    self.removeItem(conn_item)
            except Exception:
                pass

        # 2. Удаляем узлы
        for node_item in list(self.node_items.values()):
            try:
                if node_item.scene() is self:
                    self.removeItem(node_item)
            except Exception:
                pass

        self.node_items.clear()
        self.connection_items.clear()

        if dialogue is None:
            return

        # 3. Узлы
        for model_node in dialogue.nodes.values():
            self._add_node_item(model_node)

        # 4. Связи (после узлов — чтобы порты уже существовали)
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
