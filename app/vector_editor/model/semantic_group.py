"""
SemanticGroup — именованная группа узлов внутри Asset'а.

Пример: «Основание» → n_000, n_001, n_002, n_003.
Не дублирует рёбра — они вычисляются из node_ids.

Один узел может входить в несколько групп.
"""

from __future__ import annotations

import uuid


class SemanticGroup:
    """Именованная группа узлов."""

    def __init__(
        self,
        id: str | None = None,
        name: str = "group",
        label: str = "Группа",
        node_ids: list[str] | None = None,
    ):
        self.id = id or self._generate_id()
        self.name = name          # slug-имя (foundation, left_wall)
        self.label = label        # человекочитаемое
        self.node_ids = list(node_ids or [])

    @staticmethod
    def _generate_id() -> str:
        return "g_" + uuid.uuid4().hex[:8]

    # ------------------------------------------------------------

    def contains(self, node_id: str) -> bool:
        return node_id in self.node_ids

    def add_node(self, node_id: str) -> bool:
        if node_id in self.node_ids:
            return False
        self.node_ids.append(node_id)
        return True

    def remove_node(self, node_id: str) -> bool:
        if node_id not in self.node_ids:
            return False
        self.node_ids.remove(node_id)
        return True

    def count(self) -> int:
        return len(self.node_ids)

    # ------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "label": self.label,
            "node_ids": list(self.node_ids),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SemanticGroup":
        return cls(
            id=d.get("id"),
            name=d.get("name", "group"),
            label=d.get("label", "Группа"),
            node_ids=list(d.get("node_ids", [])),
        )
