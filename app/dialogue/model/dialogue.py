"""
Класс Dialogue — контейнер для узлов и связей диалогового графа.

Модель данных. Не знает о Qt, о QGraphicsItem, о view.
Содержит: id, name, description, nodes (dict по id), connections (list).
"""

from .node import DialogueNode
from .connection import DialogueConnection


class Dialogue:
    """Диалог — граф из узлов и связей."""

    def __init__(
        self,
        dialogue_id,
        name="",
        description="",
        tags=None,
        entry_conditions=None,
    ):
        self.id = dialogue_id
        self.name = name
        self.description = description

        # v3: метаданные проекта диалога
        self.tags = list(tags) if tags else []
        # entry_conditions = None | {"logic": "AND"|"OR", "items": [...]}
        self.entry_conditions = entry_conditions

        # Узлы хранятся по ID для быстрого доступа O(1)
        self.nodes = {}          # dict[node_id, DialogueNode]

        # Связи — список. Доступ по ID не критичен, их обычно мало.
        self.connections = []    # list[DialogueConnection]

    # =========================================================
    # NODES
    # =========================================================

    def add_node(self, node):
        """Добавляет узел. Если такой id уже есть — ошибка."""
        if node.id in self.nodes:
            raise ValueError(f"Node with id={node.id!r} already exists")
        self.nodes[node.id] = node

    def remove_node(self, node_id):
        """Удаляет узел и все связанные с ним связи."""
        if node_id not in self.nodes:
            return None
        node = self.nodes.pop(node_id)
        # Удаляем все связи, где этот узел — source или target
        self.connections = [
            c for c in self.connections
            if c.source_node_id != node_id and c.target_node_id != node_id
        ]
        return node

    def get_node(self, node_id):
        """Возвращает узел по id или None."""
        return self.nodes.get(node_id)

    def has_node(self, node_id):
        return node_id in self.nodes

    # =========================================================
    # CONNECTIONS
    # =========================================================

    def add_connection(self, connection):
        """Добавляет связь."""
        self.connections.append(connection)

    def remove_connection(self, connection_id):
        """Удаляет связь по id. Возвращает удалённую или None."""
        for i, c in enumerate(self.connections):
            if c.id == connection_id:
                return self.connections.pop(i)
        return None

    def get_connection(self, connection_id):
        for c in self.connections:
            if c.id == connection_id:
                return c
        return None

    def find_connection(self, source_node_id, source_port):
        """Ищет связь по source. Для проверки 'один output = одна связь'."""
        for c in self.connections:
            if (
                c.source_node_id == source_node_id
                and c.source_port == source_port
            ):
                return c
        return None

    def find_connections_from_node(self, node_id):
        """Все связи, исходящие из узла."""
        return [c for c in self.connections if c.source_node_id == node_id]

    def find_connections_to_node(self, node_id):
        """Все связи, входящие в узел."""
        return [c for c in self.connections if c.target_node_id == node_id]

    # =========================================================
    # SERIALIZATION
    # =========================================================

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tags": list(self.tags),
            "entry_conditions": self.entry_conditions,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "connections": [c.to_dict() for c in self.connections],
        }

    @classmethod
    def from_dict(cls, data):
        # v3: tags, entry_conditions
        tags_raw = data.get("tags", [])
        if not isinstance(tags_raw, list):
            tags_raw = []

        entry_conditions = data.get("entry_conditions")
        if entry_conditions is not None and not isinstance(
            entry_conditions, dict
        ):
            entry_conditions = None

        dialogue = cls(
            dialogue_id=data["id"],
            name=data.get("name", ""),
            description=data.get("description", ""),
            tags=tags_raw,
            entry_conditions=entry_conditions,
        )
        for node_data in data.get("nodes", []):
            node = DialogueNode.from_dict(node_data)
            dialogue.nodes[node.id] = node
        for conn_data in data.get("connections", []):
            conn = DialogueConnection.from_dict(conn_data)
            dialogue.connections.append(conn)
        return dialogue

    def __repr__(self):
        return (
            f"<Dialogue id={self.id!r} name={self.name!r} "
            f"nodes={len(self.nodes)} connections={len(self.connections)}>"
        )
