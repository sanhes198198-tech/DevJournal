"""
Узлы диалогового графа.

Модель данных — не зависит от Qt (QGraphicsItem).
Каждый узел — это чистая структура с полями и методами
сериализации в dict / из dict.
"""

from ..ids import generate_option_id


# =========================================================
# БАЗОВЫЙ УЗЕЛ
# =========================================================

class DialogueNode:
    """Базовый узел диалога."""

    type = "base"

    def __init__(self, node_id, x=0.0, y=0.0):
        self.id = node_id
        self.x = float(x)
        self.y = float(y)

    def get_input_ports(self):
        """Список входных портов (по умолчанию — нет)."""
        return []

    def get_output_ports(self):
        """Список выходных портов (по умолчанию — нет)."""
        return []

    def to_dict(self):
        """Базовая сериализация. Переопределяется в подтипах."""
        return {
            "id": self.id,
            "type": self.type,
            "x": self.x,
            "y": self.y,
        }

    @classmethod
    def _from_dict(cls, data):
        """Базовая десериализация. Переопределяется в подтипах."""
        return cls(
            node_id=data["id"],
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
        )

    @classmethod
    def from_dict(cls, data):
        """Универсальная десериализация — выбирает подтип по 'type'."""
        node_type = data.get("type")
        target = NODE_TYPE_MAP.get(node_type)
        if target is None:
            raise ValueError(f"Unknown node type: {node_type!r}")
        return target._from_dict(data)

    def __repr__(self):
        return f"<{type(self).__name__} id={self.id!r}>"


# =========================================================
# START
# =========================================================

class StartNode(DialogueNode):
    """Точка входа диалога."""

    type = "start"

    def get_input_ports(self):
        return []

    def get_output_ports(self):
        return ["output"]


# =========================================================
# REPLY (обычная реплика)
# =========================================================

class ReplyNode(DialogueNode):
    """Реплика персонажа."""

    type = "reply"

    def __init__(
        self,
        node_id,
        speaker="",
        text="",
        presentation=None,
        x=0.0,
        y=0.0,
    ):
        super().__init__(node_id, x, y)
        self.speaker = speaker
        self.text = text

        # presentation: dict — контейнер для будущих визуальных данных
        # (портрет, эмоция, позиция). MVP не интерпретирует, но сохраняет.
        self.presentation = (
            dict(presentation) if presentation else {}
        )

    def get_input_ports(self):
        return ["input"]

    def get_output_ports(self):
        return ["output"]

    def to_dict(self):
        data = super().to_dict()
        data["speaker"] = self.speaker
        data["text"] = self.text
        data["presentation"] = dict(self.presentation)
        return data

    @classmethod
    def _from_dict(cls, data):
        presentation_raw = data.get("presentation", {})

        if presentation_raw is None:
            presentation_raw = {}
        elif not isinstance(presentation_raw, dict):
            # Некорректный формат — сбрасываем в пустой dict
            presentation_raw = {}

        return cls(
            node_id=data["id"],
            speaker=data.get("speaker", ""),
            text=data.get("text", ""),
            presentation=presentation_raw,
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
        )


# =========================================================
# CHOICE
# =========================================================

class ChoiceOption:
    """Один вариант выбора внутри ChoiceNode."""

    def __init__(
        self,
        option_id,
        text="",
        order=0,
        condition=None,
        effects=None,
    ):
        self.id = option_id
        self.text = text
        self.order = int(order)

        # Архитектурный контракт:
        # condition и effects существуют, но MVP их не интерпретирует.
        # condition: object | None — структура условия (задел)
        # effects: list — упорядоченный список игровых операций (задел)
        self.condition = condition
        self.effects = list(effects) if effects else []

    def to_dict(self):
        return {
            "id": self.id,
            "text": self.text,
            "order": self.order,
            "condition": self.condition,
            "effects": list(self.effects),
        }

    @classmethod
    def from_dict(cls, data):
        # Проверка типов для известных полей (forward compat с защитой)
        effects_raw = data.get("effects", [])

        if effects_raw is None:
            effects_raw = []
        elif not isinstance(effects_raw, list):
            # Некорректный формат — сбрасываем в пустой список
            effects_raw = []

        return cls(
            option_id=data["id"],
            text=data.get("text", ""),
            order=data.get("order", 0),
            condition=data.get("condition"),
            effects=effects_raw,
        )

    def __repr__(self):
        return f"<ChoiceOption id={self.id!r} text={self.text!r}>"


class ChoiceNode(DialogueNode):
    """Узел выбора с N вариантами (options)."""

    type = "choice"

    def __init__(self, node_id, question="", options=None, x=0.0, y=0.0):
        super().__init__(node_id, x, y)
        self.question = question
        self.options = list(options) if options else []

    def get_input_ports(self):
        return ["input"]

    def get_output_ports(self):
        return [f"opt_{opt.id}" for opt in self.options]

    def add_option(self, text=""):
        """Добавляет новый вариант с новым ID и order в конце."""
        order = max((o.order for o in self.options), default=-1) + 1
        opt = ChoiceOption(generate_option_id(), text=text, order=order)
        self.options.append(opt)
        return opt

    def remove_option(self, option_id):
        """Удаляет вариант по ID."""
        self.options = [o for o in self.options if o.id != option_id]

    def get_option(self, option_id):
        for o in self.options:
            if o.id == option_id:
                return o
        return None

    def sort_options(self):
        """Сортирует варианты по order."""
        self.options.sort(key=lambda o: o.order)

    def to_dict(self):
        data = super().to_dict()
        data["question"] = self.question
        data["options"] = [o.to_dict() for o in self.options]
        return data

    @classmethod
    def _from_dict(cls, data):
        options = [ChoiceOption.from_dict(o) for o in data.get("options", [])]
        node = cls(
            node_id=data["id"],
            question=data.get("question", ""),
            options=options,
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
        )
        node.sort_options()
        return node


# =========================================================
# END
# =========================================================

class EndNode(DialogueNode):
    """Точка завершения диалога."""

    type = "end"

    # Архитектурный контракт:
    #   outcome == "end"       → target_dialogue_id = None
    #   outcome == "dialogue"  → target_dialogue_id = <uuid>
    # MVP интерпретирует только "end".
    VALID_OUTCOMES = ("end", "dialogue")

    def __init__(
        self,
        node_id,
        outcome="end",
        target_dialogue_id=None,
        x=0.0,
        y=0.0,
    ):
        super().__init__(node_id, x, y)

        if outcome not in self.VALID_OUTCOMES:
            outcome = "end"

        self.outcome = outcome
        self.target_dialogue_id = target_dialogue_id

    def get_input_ports(self):
        return ["input"]

    def get_output_ports(self):
        return []

    def to_dict(self):
        data = super().to_dict()
        data["outcome"] = self.outcome
        data["target_dialogue_id"] = self.target_dialogue_id
        return data

    @classmethod
    def _from_dict(cls, data):
        outcome = data.get("outcome", "end")

        if outcome not in cls.VALID_OUTCOMES:
            outcome = "end"

        target = data.get("target_dialogue_id")

        # Защита от несоответствия
        if outcome == "end":
            target = None

        return cls(
            node_id=data["id"],
            outcome=outcome,
            target_dialogue_id=target,
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
        )


# =========================================================
# РЕЕСТР ТИПОВ
# =========================================================
# Заполняется после определения всех классов.
# Используется в DialogueNode.from_dict().

NODE_TYPE_MAP = {
    "start": StartNode,
    "reply": ReplyNode,
    "choice": ChoiceNode,
    "end": EndNode,
}
