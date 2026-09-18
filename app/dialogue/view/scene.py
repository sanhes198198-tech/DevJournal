"""
QGraphicsScene для редактора диалогов.

Собирает визуальные узлы (DialogueNodeItem) и связи
(DialogueConnectionItem) из модели Dialogue.

Отслеживает движение узлов и обновляет пути связей.
"""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtWidgets import QGraphicsScene, QMenu

from .node_item import DialogueNodeItem
from .connection_item import DialogueConnectionItem
from .port_item import PortItem

from ..commands import (
    CreateNodeCommand,
    DeleteNodeCommand,
    DeleteConnectionCommand,
    CreateConnectionCommand,
    MoveNodeCommand,
)
from ..ids import generate_node_id, generate_connection_id, generate_option_id
from ..model import StartNode, ReplyNode, ChoiceNode, EndNode, DialogueConnection, DialogueNode


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

        # Состояние drag-создания связи
        self._drag_source_port = None
        self._temp_line = None

        # Внутренний буфер копирования узлов
        self._clipboard = None

        # Ссылка на undo_stack (для макросов при вставке)
        self._undo_stack = None

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

    def set_command_sink(self, sink, undo_stack=None):
        """sink — callable(command) или None. undo_stack — для макросов."""
        self._command_sink = sink
        self._undo_stack = undo_stack

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
    # ПЕРЕМЕЩЕНИЕ УЗЛА (через команду)
    # =========================================================

    def push_move_command(self, node_item, old_pos, new_pos):
        """
        Создаёт MoveNodeCommand для перетаскивания узла.

        old_pos / new_pos — QPointF из visual.
        Команда пишет координаты в модель и обновляет visual через notify.
        """
        if self.dialogue is None:
            return

        node = self.dialogue.get_node(node_item.node_id)
        if node is None:
            return

        def _notify():
            # Приводим visual в соответствие с моделью (для undo/redo)
            item = self.node_items.get(node.id)
            if item is not None:
                from PySide6.QtCore import QPointF
                item.setPos(QPointF(node.x, node.y))

            self.on_node_moved(node.id)

        cmd = MoveNodeCommand(
            node=node,
            old_pos=(float(old_pos.x()), float(old_pos.y())),
            new_pos=(float(new_pos.x()), float(new_pos.y())),
            notify=_notify,
        )
        self._push(cmd)

    # =========================================================
    # DRAG-СОЗДАНИЕ СВЯЗИ
    # =========================================================

    def _find_port_at(self, scene_pos):
        """Находит PortItem в точке сцены."""
        for item in self.items(scene_pos):
            if isinstance(item, PortItem):
                return item
        return None

    def begin_connection_drag(self, source_port):
        """Начинает drag-создание связи от output-порта."""
        if source_port.is_input:
            return

        self._drag_source_port = source_port

        from PySide6.QtGui import QPainterPath, QPen, QColor
        from PySide6.QtWidgets import QGraphicsPathItem

        path = QPainterPath()
        start = source_port.scene_center()
        path.moveTo(start)
        path.lineTo(start)

        line = QGraphicsPathItem(path)
        pen = QPen(QColor("#4F7CFF"), 2.0)
        pen.setStyle(Qt.PenStyle.DashLine)
        line.setPen(pen)
        line.setZValue(100)
        self.addItem(line)

        self._temp_line = line

    def update_connection_drag(self, scene_pos):
        """Обновляет временную линию до курсора."""
        if self._temp_line is None or self._drag_source_port is None:
            return

        from PySide6.QtGui import QPainterPath
        from PySide6.QtCore import QPointF

        start = self._drag_source_port.scene_center()
        end = QPointF(scene_pos)

        path = QPainterPath()
        path.moveTo(start)
        path.lineTo(end)

        self._temp_line.setPath(path)

    def end_connection_drag(self, scene_pos):
        """Завершает drag — создаёт связь, если попали в input-порт."""
        if self._drag_source_port is None:
            self._cleanup_connection_drag()
            return

        target_port = self._find_port_at(scene_pos)

        if target_port is not None:
            self._try_create_connection(
                self._drag_source_port,
                target_port,
            )

        self._cleanup_connection_drag()

    def _cleanup_connection_drag(self):
        if self._temp_line is not None:
            try:
                self.removeItem(self._temp_line)
            except Exception:
                pass
            self._temp_line = None

        self._drag_source_port = None

    def _try_create_connection(self, src_port, tgt_port):
        """Проверяет правила и создаёт связь через команду."""
        if self.dialogue is None:
            return

        # Целевой порт должен быть input
        if not tgt_port.is_input:
            return

        # Source не может быть input
        if src_port.is_input:
            return

        # Нельзя соединить узел сам с собой
        if src_port.node_id == tgt_port.node_id:
            return

        # Проверка: у source-порта уже есть связь?
        existing = self.dialogue.find_connection(
            src_port.node_id,
            src_port.port_name,
        )
        if existing is not None:
            return

        # Создаём модель связи
        conn = DialogueConnection(
            connection_id=generate_connection_id(),
            source_node_id=src_port.node_id,
            source_port=src_port.port_name,
            target_node_id=tgt_port.node_id,
            target_port=tgt_port.port_name,
        )

        def _notify():
            self._sync_connection_visual(conn)

        cmd = CreateConnectionCommand(
            dialogue=self.dialogue,
            connection=conn,
            notify=_notify,
        )
        self._push(cmd)

    # =========================================================
    # ПОИСК УЗЛОВ (Ctrl+F)
    # =========================================================

    @staticmethod
    def _node_matches_query(node, query_lower):
        """Проверяет, содержит ли узел query (регистр не важен)."""
        t = node.type

        if t == "reply":
            speaker = (getattr(node, "speaker", "") or "").lower()
            text = (getattr(node, "text", "") or "").lower()
            return query_lower in speaker or query_lower in text

        if t == "choice":
            question = (getattr(node, "question", "") or "").lower()
            if query_lower in question:
                return True
            for opt in getattr(node, "options", []):
                opt_text = (getattr(opt, "text", "") or "").lower()
                if query_lower in opt_text:
                    return True

        return False

    def find_nodes(self, query):
        """
        Возвращает список node_id, чьи тексты содержат query.

        Поиск идёт по:
          - ReplyNode: speaker + text
          - ChoiceNode: question + options[].text
        Регистр не важен.
        """
        if self.dialogue is None:
            return []

        if not query or not query.strip():
            return []

        q = query.strip().lower()
        result = []

        for node in self.dialogue.nodes.values():
            if self._node_matches_query(node, q):
                result.append(node.id)

        return result

    # =========================================================
    # COPY / CUT / PASTE (Ctrl+C / Ctrl+X / Ctrl+V)
    # =========================================================

    def copy_selected(self):
        """Копирует выделенные узлы + связи между ними во внутренний буфер."""
        if self.dialogue is None:
            return

        selected_items = self.get_selected_node_items()
        selected_ids = {item.node_id for item in selected_items}

        if not selected_ids:
            self._clipboard = None
            return

        # Узлы
        nodes_data = []
        for nid in selected_ids:
            node = self.dialogue.get_node(nid)
            if node is not None:
                nodes_data.append(node.to_dict())

        # Только ВНУТРЕННИЕ связи (оба конца выделены)
        conns_data = []
        for c in self.dialogue.connections:
            if (
                c.source_node_id in selected_ids
                and c.target_node_id in selected_ids
            ):
                conns_data.append(c.to_dict())

        self._clipboard = {
            "nodes": nodes_data,
            "connections": conns_data,
        }

    def cut_selected(self):
        """Копирует + удаляет выделенные узлы."""
        self.copy_selected()
        self.delete_selected()

    def paste_clipboard(self):
        """Вставляет содержимое буфера со смещением +40/+40."""
        if self.dialogue is None:
            return
        if not self._clipboard:
            return

        nodes_data = self._clipboard.get("nodes", [])
        conns_data = self._clipboard.get("connections", [])

        if not nodes_data:
            return

        # --- Готовим новые ID для узлов и опций ---
        node_id_map = {}      # old_node_id -> new_node_id
        option_id_map = {}    # old_option_id -> new_option_id

        new_nodes = []

        for nd in nodes_data:
            old_id = nd["id"]
            new_id = generate_node_id()
            node_id_map[old_id] = new_id

            new_data = dict(nd)
            new_data["id"] = new_id
            new_data["x"] = float(new_data.get("x", 0.0)) + 40.0
            new_data["y"] = float(new_data.get("y", 0.0)) + 40.0

            # Для choice — пересоздать option_ids
            if new_data.get("type") == "choice":
                new_options = []
                for opt_data in new_data.get("options", []):
                    new_opt = dict(opt_data)
                    old_opt_id = new_opt.get("id", "")
                    new_opt_id = generate_option_id()
                    option_id_map[old_opt_id] = new_opt_id
                    new_opt["id"] = new_opt_id
                    new_options.append(new_opt)
                new_data["options"] = new_options

            new_nodes.append(DialogueNode.from_dict(new_data))

        # --- Открываем макрос (одна команда для Ctrl+Z) ---
        if self._undo_stack is not None:
            try:
                self._undo_stack.beginMacro("Paste")
            except Exception:
                pass

        new_node_ids = []

        try:
            # Создаём новые узлы
            for node in new_nodes:
                def _notify(n=node):
                    self._sync_node_visual(n)

                cmd = CreateNodeCommand(
                    dialogue=self.dialogue,
                    node=node,
                    notify=_notify,
                )
                self._push(cmd)
                new_node_ids.append(node.id)

            # Восстанавливаем связи
            for cd in conns_data:
                old_src = cd["source_node_id"]
                old_tgt = cd["target_node_id"]

                if old_src not in node_id_map:
                    continue
                if old_tgt not in node_id_map:
                    continue

                new_src = node_id_map[old_src]
                new_tgt = node_id_map[old_tgt]

                # source_port: если choice-порт — мапим option_id
                source_port = cd["source_port"]
                if source_port.startswith("opt_"):
                    old_opt_id = source_port[4:]
                    if old_opt_id in option_id_map:
                        source_port = f"opt_{option_id_map[old_opt_id]}"

                new_conn = DialogueConnection(
                    connection_id=generate_connection_id(),
                    source_node_id=new_src,
                    source_port=source_port,
                    target_node_id=new_tgt,
                    target_port=cd["target_port"],
                )

                def _notify_conn(c=new_conn):
                    self._sync_connection_visual(c)

                cmd = CreateConnectionCommand(
                    dialogue=self.dialogue,
                    connection=new_conn,
                    notify=_notify_conn,
                )
                self._push(cmd)

        finally:
            # Закрываем макрос
            if self._undo_stack is not None:
                try:
                    self._undo_stack.endMacro()
                except Exception:
                    pass

        # Выделяем вставленные узлы
        try:
            self.clearSelection()
            for nid in new_node_ids:
                item = self.node_items.get(nid)
                if item is not None:
                    item.setSelected(True)
        except Exception:
            pass

    # =========================================================
    # ДУБЛИРОВАНИЕ УЗЛОВ (Ctrl+D)
    # =========================================================

    def duplicate_selected(self):
        """Дублирует все выделенные узлы со смещением."""
        if self.dialogue is None:
            return

        selected = self.get_selected_node_items()
        if not selected:
            return

        new_node_ids = []

        for item in selected:
            new_id = self._duplicate_node(item.node_id)
            if new_id:
                new_node_ids.append(new_id)

        # Выделить новые узлы (снять выделение со старых)
        try:
            self.clearSelection()
            for nid in new_node_ids:
                new_item = self.node_items.get(nid)
                if new_item is not None:
                    new_item.setSelected(True)
        except Exception:
            pass

    def _duplicate_node(self, source_node_id):
        """Создаёт копию узла со смещением. Возвращает новый id или None."""
        if self.dialogue is None:
            return None

        src_node = self.dialogue.get_node(source_node_id)
        if src_node is None:
            return None

        # Копируем через to_dict — сохраняет все поля
        data = src_node.to_dict()

        # Новый id узла
        new_id = generate_node_id()
        data["id"] = new_id

        # Смещение позиции
        data["x"] = float(data.get("x", 0.0)) + 40.0
        data["y"] = float(data.get("y", 0.0)) + 40.0

        # Для ChoiceNode — пересоздать option_ids
        if src_node.type == "choice":
            for opt_data in data.get("options", []):
                opt_data["id"] = generate_option_id()

        # Создаём через from_dict — вставит дефолты если что
        new_node = DialogueNode.from_dict(data)

        def _notify():
            self._sync_node_visual(new_node)

        cmd = CreateNodeCommand(
            dialogue=self.dialogue,
            node=new_node,
            notify=_notify,
        )
        self._push(cmd)

        return new_id

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
