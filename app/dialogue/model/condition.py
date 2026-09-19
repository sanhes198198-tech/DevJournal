"""
Условия для ChoiceOption.

Condition    — одно условие (сравнение переменной/флага)
ConditionGroup — группа условий с логикой AND / OR

Формат JSON:
  null | {
    "logic": "AND" | "OR",
    "items": [Condition, ...]
  }

Condition JSON:
  {
    "kind": "variable",
    "variable": "reputation",
    "operator": ">=",
    "value": 50
  }
  или
  {
    "kind": "flag",
    "flag": "knows_secret",
    "operator": "==",
    "value": true
  }
"""

VALID_KINDS = ("variable", "flag")

VALID_LOGIC = ("AND", "OR")

VALID_VARIABLE_OPERATORS = (
    "==", "!=", ">", "<", ">=", "<=",
    "contains", "is_null", "is_not_null",
)

VALID_FLAG_OPERATORS = ("==", "!=")


# =========================================================
# CONDITION
# =========================================================

class Condition:
    """Одно условие."""

    def __init__(
        self,
        kind="variable",
        operator="==",
        value=None,
        variable=None,
        flag=None,
    ):
        if kind not in VALID_KINDS:
            kind = "variable"

        self.kind = kind
        self.operator = operator
        self.value = value

        if kind == "variable":
            self.variable = variable or ""
            self.flag = None
            if operator not in VALID_VARIABLE_OPERATORS:
                self.operator = "=="
        else:
            self.flag = flag or ""
            self.variable = None
            if operator not in VALID_FLAG_OPERATORS:
                self.operator = "=="

    @property
    def target(self):
        """Имя переменной или флага."""
        if self.kind == "variable":
            return self.variable
        return self.flag

    def set_target(self, name):
        if self.kind == "variable":
            self.variable = name
        else:
            self.flag = name

    def to_dict(self):
        if self.kind == "variable":
            return {
                "kind": "variable",
                "variable": self.variable,
                "operator": self.operator,
                "value": self.value,
            }
        return {
            "kind": "flag",
            "flag": self.flag,
            "operator": self.operator,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            return None

        kind = data.get("kind", "variable")
        operator = data.get("operator", "==")
        value = data.get("value")

        if kind == "flag":
            return cls(
                kind="flag",
                operator=operator,
                value=value,
                flag=data.get("flag", ""),
            )

        return cls(
            kind="variable",
            operator=operator,
            value=value,
            variable=data.get("variable", ""),
        )

    def __repr__(self):
        return (
            f"<Condition {self.kind} {self.target!r} "
            f"{self.operator} {self.value!r}>"
        )


# =========================================================
# CONDITION GROUP
# =========================================================

class ConditionGroup:
    """Группа условий с логикой AND/OR."""

    def __init__(self, logic="AND", items=None):
        if logic not in VALID_LOGIC:
            logic = "AND"

        self.logic = logic
        self.items = []

        if items:
            for it in items:
                if isinstance(it, Condition):
                    self.items.append(it)
                elif isinstance(it, dict):
                    cond = Condition.from_dict(it)
                    if cond is not None:
                        self.items.append(cond)

    def add(self, condition):
        if isinstance(condition, Condition):
            self.items.append(condition)

    def remove(self, index):
        if 0 <= index < len(self.items):
            self.items.pop(index)

    def get(self, index):
        if 0 <= index < len(self.items):
            return self.items[index]
        return None

    def is_empty(self):
        return len(self.items) == 0

    def __len__(self):
        return len(self.items)

    def to_dict(self):
        if self.is_empty():
            return None
        return {
            "logic": self.logic,
            "items": [c.to_dict() for c in self.items],
        }

    @classmethod
    def from_dict(cls, data):
        """None или не dict → None. Пустая группа → None."""
        if data is None or not isinstance(data, dict):
            return None

        items_raw = data.get("items", [])
        if not isinstance(items_raw, list) or not items_raw:
            return None

        group = cls(
            logic=data.get("logic", "AND"),
            items=items_raw,
        )

        if group.is_empty():
            return None

        return group

    def __repr__(self):
        return f"<ConditionGroup {self.logic} items={len(self.items)}>"