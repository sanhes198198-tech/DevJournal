"""
Project-level данные для dialogue системы.

Это НЕ часть отдельного диалога, а общие данные проекта:
  - characters — справочник персонажей
  - variables — числовые/строковые переменные игры
  - flags — булевы флаги

Схема имеет свою schema_version, независимую от Dialogue Schema.
"""

PROJECT_DATA_SCHEMA_VERSION = 1


# =========================================================
# CHARACTER
# =========================================================

class Character:
    """Персонаж — запись в справочнике."""

    def __init__(
        self,
        character_id,
        name="",
        description="",
        portrait_default=None,
    ):
        self.id = character_id
        self.name = name
        self.description = description
        self.portrait_default = portrait_default

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "portrait_default": self.portrait_default,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            character_id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            portrait_default=data.get("portrait_default"),
        )

    def __repr__(self):
        return f"<Character id={self.id!r} name={self.name!r}>"


# =========================================================
# VARIABLE
# =========================================================

VALID_VARIABLE_TYPES = ("int", "float", "bool", "string")


class Variable:
    """Переменная игры — числовая или строковая."""

    def __init__(
        self,
        variable_id,
        var_type="int",
        default=0,
        label="",
    ):
        self.id = variable_id

        if var_type not in VALID_VARIABLE_TYPES:
            var_type = "int"

        self.type = var_type
        self.default = default
        self.label = label

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "default": self.default,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            variable_id=data.get("id", ""),
            var_type=data.get("type", "int"),
            default=data.get("default", 0),
            label=data.get("label", ""),
        )

    def __repr__(self):
        return f"<Variable id={self.id!r} type={self.type!r}>"


# =========================================================
# FLAG
# =========================================================

class Flag:
    """Булев флаг — knows_secret, met_irina и т.п."""

    def __init__(self, flag_id, default=False, label=""):
        self.id = flag_id
        self.default = bool(default)
        self.label = label

    def to_dict(self):
        return {
            "id": self.id,
            "default": self.default,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            flag_id=data.get("id", ""),
            default=data.get("default", False),
            label=data.get("label", ""),
        )

    def __repr__(self):
        return f"<Flag id={self.id!r}>"


# =========================================================
# PROJECT DATA — контейнер
# =========================================================

class ProjectData:
    """Общие данные проекта: персонажи, переменные, флаги."""

    def __init__(self):
        self.characters = {}
        self.variables = {}
        self.flags = {}

    # --- characters ---

    def add_character(self, character):
        self.characters[character.id] = character

    def get_character(self, character_id):
        return self.characters.get(character_id)

    def remove_character(self, character_id):
        return self.characters.pop(character_id, None)

    # --- variables ---

    def add_variable(self, variable):
        self.variables[variable.id] = variable

    def get_variable(self, variable_id):
        return self.variables.get(variable_id)

    def remove_variable(self, variable_id):
        return self.variables.pop(variable_id, None)

    # --- flags ---

    def add_flag(self, flag):
        self.flags[flag.id] = flag

    def get_flag(self, flag_id):
        return self.flags.get(flag_id)

    def remove_flag(self, flag_id):
        return self.flags.pop(flag_id, None)

    # --- serialization ---

    def to_dict(self):
        return {
            "schema_version": PROJECT_DATA_SCHEMA_VERSION,
            "characters": [
                c.to_dict() for c in self.characters.values()
            ],
            "variables": [
                v.to_dict() for v in self.variables.values()
            ],
            "flags": [
                f.to_dict() for f in self.flags.values()
            ],
        }

    @classmethod
    def from_dict(cls, data):
        pd = cls()

        if not isinstance(data, dict):
            return pd

        chars_raw = data.get("characters", [])
        if not isinstance(chars_raw, list):
            chars_raw = []

        for c_data in chars_raw:
            if isinstance(c_data, dict):
                c = Character.from_dict(c_data)
                pd.characters[c.id] = c

        vars_raw = data.get("variables", [])
        if not isinstance(vars_raw, list):
            vars_raw = []

        for v_data in vars_raw:
            if isinstance(v_data, dict):
                v = Variable.from_dict(v_data)
                pd.variables[v.id] = v

        flags_raw = data.get("flags", [])
        if not isinstance(flags_raw, list):
            flags_raw = []

        for f_data in flags_raw:
            if isinstance(f_data, dict):
                f = Flag.from_dict(f_data)
                pd.flags[f.id] = f

        return pd

    # --- resolve ---

    def resolve_speaker_name(self, speaker_id):
        """
        Возвращает человекочитаемое имя персонажа по его ID.

        Fallback:
          - пустой id → "???"
          - нет в справочнике → сам id (slug)
        """
        if not speaker_id:
            return "???"

        char = self.characters.get(speaker_id)
        if char is not None and char.name:
            return char.name

        return speaker_id

    def __repr__(self):
        return (
            f"<ProjectData "
            f"characters={len(self.characters)} "
            f"variables={len(self.variables)} "
            f"flags={len(self.flags)}>"
        )