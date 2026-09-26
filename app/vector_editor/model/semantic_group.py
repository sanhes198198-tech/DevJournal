"""
SemanticGroup — именованная группа узлов внутри Asset'а.

Пример: «Основание» → n_000, n_001, n_002, n_003.
Не дублирует рёбра — они вычисляются из node_ids.

Один узел может входить в несколько групп.
"""

from __future__ import annotations

from copy import deepcopy
import uuid


_AUTO_RULE_MISSING = object()


class SemanticGroup:
    """Именованная группа узлов."""

    def __init__(
        self,
        id: str | None = None,
        name: str = "group",
        label: str = "Группа",
        node_ids: list[str] | None = None,
        auto_rule: dict | None | object = _AUTO_RULE_MISSING,
    ):
        self.id = id or self._generate_id()
        self.name = name          # slug-имя (foundation, left_wall)
        self.label = label        # человекочитаемое
        self.node_ids = list(node_ids or [])
        # Keep the distinction between an absent legacy key and explicit
        # ``null`` so loading and saving an Asset cannot erase either form.
        self._has_auto_rule = auto_rule is not _AUTO_RULE_MISSING
        self._auto_rule: dict | None = None
        if self._has_auto_rule:
            self._auto_rule = deepcopy(auto_rule)

    @property
    def auto_rule(self) -> dict | None:
        """Legacy auto-rule preserved for migration and JSON round-trips."""
        return self._auto_rule

    @auto_rule.setter
    def auto_rule(self, value: dict | None) -> None:
        self._auto_rule = deepcopy(value)
        self._has_auto_rule = True

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
        data = {
            "id": self.id,
            "name": self.name,
            "label": self.label,
            "node_ids": list(self.node_ids),
        }
        if self._has_auto_rule:
            data["auto_rule"] = deepcopy(self.auto_rule)
        return data

    @classmethod
    def from_dict(cls, d: dict) -> "SemanticGroup":
        return cls(
            id=d.get("id"),
            name=d.get("name", "group"),
            label=d.get("label", "Группа"),
            node_ids=list(d.get("node_ids", [])),
            auto_rule=(
                d["auto_rule"]
                if "auto_rule" in d
                else _AUTO_RULE_MISSING
            ),
        )
