"""
Связь между узлами диалогового графа.

Связь идентифицируется парой (source_node_id, source_port).
Позиции узлов не влияют на связи — только ID.
"""


class DialogueConnection:
    """Одно направленное соединение между двумя узлами."""

    def __init__(
        self,
        connection_id,
        source_node_id,
        source_port,
        target_node_id,
        target_port,
    ):
        self.id = connection_id
        self.source_node_id = source_node_id
        self.source_port = source_port
        self.target_node_id = target_node_id
        self.target_port = target_port

    def to_dict(self):
        return {
            "id": self.id,
            "source_node_id": self.source_node_id,
            "source_port": self.source_port,
            "target_node_id": self.target_node_id,
            "target_port": self.target_port,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            connection_id=data["id"],
            source_node_id=data["source_node_id"],
            source_port=data["source_port"],
            target_node_id=data["target_node_id"],
            target_port=data["target_port"],
        )

    def __repr__(self):
        return (
            f"<DialogueConnection id={self.id!r} "
            f"{self.source_node_id}:{self.source_port} -> "
            f"{self.target_node_id}:{self.target_port}>"
        )
