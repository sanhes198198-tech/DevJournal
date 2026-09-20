"""
VisibilityRule — правило показа/скрытия компонентов композита
на основе значения параметра одного из под-ассетов.

Пример:
  component_id    = "c_wall_1"       — чей параметр смотрим
  parameter_name  = "height"         — какой параметр
  operator        = ">"
  value           = 15.0
  show_ids        = ["c_roof_tall"]  — показать, когда условие True
  hide_ids        = ["c_roof_flat"]  — скрыть, когда условие True

Если условие False — действия инвертируются:
  show_ids → скрыть
  hide_ids → показать
"""

from __future__ import annotations

import uuid


VALID_OPERATORS = (">", "<", ">=", "<=", "==", "!=")


class VisibilityRule:
    """Правило показа/скрытия компонентов по условию."""

    def __init__(
        self,
        id: str | None = None,
        name: str = "rule",
        label: str = "Правило",
        component_id: str = "",
        parameter_name: str = "",
        operator: str = ">",
        value: float = 0.0,
        show_ids: list[str] | None = None,
        hide_ids: list[str] | None = None,
        enabled: bool = True,
    ):
        self.id = id or self._generate_id()
        self.name = name
        self.label = label
        # какой компонент композита отслеживаем
        self.component_id = component_id
        # какой его параметр
        self.parameter_name = parameter_name
        # условие
        self.operator = operator if operator in VALID_OPERATORS else ">"
        self.value = float(value)
        # действия при condition == True
        self.show_ids: list[str] = list(show_ids or [])
        self.hide_ids: list[str] = list(hide_ids or [])
        self.enabled = bool(enabled)

    @staticmethod
    def _generate_id() -> str:
        return "r_" + uuid.uuid4().hex[:8]

    # ------------------------------------------------------------

    def is_valid(self) -> bool:
        """Базовая проверка — есть на что смотреть и что делать."""
        if not self.component_id or not self.parameter_name:
            return False
        if not self.show_ids and not self.hide_ids:
            return False
        return True

    def evaluate(self, param_value: float) -> bool:
        """True, если условие выполнено."""
        op = self.operator
        v = self.value
        if op == ">":
            return param_value > v
        if op == "<":
            return param_value < v
        if op == ">=":
            return param_value >= v
        if op == "<=":
            return param_value <= v
        if op == "==":
            return abs(param_value - v) < 1e-6
        if op == "!=":
            return abs(param_value - v) >= 1e-6
        return False

    def action_for(
        self, comp_id: str, condition: bool,
    ) -> str | None:
        """Что делать с компонентом comp_id.

        Возвращает "show" | "hide" | None (не трогать).
        При condition=False действия инвертируются.
        """
        if condition:
            if comp_id in self.show_ids:
                return "show"
            if comp_id in self.hide_ids:
                return "hide"
        else:
            if comp_id in self.show_ids:
                return "hide"
            if comp_id in self.hide_ids:
                return "show"
        return None

    # ------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "label": self.label,
            "component_id": self.component_id,
            "parameter_name": self.parameter_name,
            "operator": self.operator,
            "value": self.value,
            "show_ids": list(self.show_ids),
            "hide_ids": list(self.hide_ids),
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VisibilityRule":
        return cls(
            id=d.get("id"),
            name=d.get("name", "rule"),
            label=d.get("label", "Правило"),
            component_id=d.get("component_id", ""),
            parameter_name=d.get("parameter_name", ""),
            operator=d.get("operator", ">"),
            value=float(d.get("value", 0.0)),
            show_ids=list(d.get("show_ids", [])),
            hide_ids=list(d.get("hide_ids", [])),
            enabled=bool(d.get("enabled", True)),
        )
