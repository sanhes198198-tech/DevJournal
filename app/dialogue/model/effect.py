"""
Effects для ChoiceOption.

Effect — одно действие (изменение переменной или флага).

Формат JSON:
  {
    "kind": "variable",
    "variable": "trust_vasilisa",
    "operation": "add",
    "value": 5
  }
  или
  {
    "kind": "flag",
    "flag": "met_irina",
    "operation": "set",
    "value": true
  }
"""

VALID_KINDS = ("variable", "flag")

VALID_VARIABLE_OPERATIONS = (
    "set", "add", "subtract", "multiply",
)

VALID_FLAG_OPERATIONS = ("set", "toggle")


# =========================================================
# EFFECT
# =========================================================

class Effect:
    """Одно действие."""

    def __init__(
        self,
        kind="variable",
        operation="set",
        value=None,
        variable=None,
        flag=None,
    ):
        if kind not in VALID_KINDS:
            kind = "variable"

        self.kind = kind
        self.operation = operation
        self.value = value

        if kind == "variable":
            self.variable = variable or ""
            self.flag = None
            if operation not in VALID_VARIABLE_OPERATIONS:
                self.operation = "set"
        else:
            self.flag = flag or ""
            self.variable = None
            if operation not in VALID_FLAG_OPERATIONS:
                self.operation = "set"

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
                "operation": self.operation,
                "value": self.value,
            }
        return {
            "kind": "flag",
            "flag": self.flag,
            "operation": self.operation,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            return None

        kind = data.get("kind", "variable")
        operation = data.get("operation", "set")
        value = data.get("value")

        if kind == "flag":
            return cls(
                kind="flag",
                operation=operation,
                value=value,
                flag=data.get("flag", ""),
            )

        return cls(
            kind="variable",
            operation=operation,
            value=value,
            variable=data.get("variable", ""),
        )

    def __repr__(self):
        return (
            f"<Effect {self.kind} {self.target!r} "
            f"{self.operation} {self.value!r}>"
        )