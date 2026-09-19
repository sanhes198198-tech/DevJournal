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
        speaker_id="",
        text="",
        presentation=None,
        x=0.0,
        y=0.0,
    ):
        super().__init__(node_id, x, y)

        # Канон v3: speaker_id (slug). Строка speaker не хранится.
        self.speaker_id = speaker_id or ""
        self.text = text

        # presentation: dict — контейнер для будущих визуальных данных
        # (портрет, эмоция, позиция). MVP не интерпретирует, но сохраняет.
        self.presentation = (
            dict(presentation) if presentation else {}
        )

    # --- Legacy alias для v2 API ---
    # Весь существующий UI читает/пишет node.speaker.
    # В v3 это property → speaker_id (slug).
    # Ничего в UI менять не нужно.

    @property
    def speaker(self):
        """Legacy alias на speaker_id. Возвращает slug."""
        return self.speaker_id

    @speaker.setter
    def speaker(self, value):
        """Legacy setter. Принимает raw name, конвертирует в slug."""
        if not value:
            self.speaker_id = ""
            return

        # Пробуем slugify через storage (ленивый импорт)
        try:
            from ..io.storage import _slugify
            self.speaker_id = _slugify(value)
        except Exception:
            # Fallback — сохранить как есть
            self.speaker_id = str(value).strip()

    def get_input_ports(self):
        return ["input"]

    def get_output_ports(self):
        return ["output"]

    def to_dict(self):
        data = super().to_dict()
        data["speaker_id"] = self.speaker_id
        data["text"] = self.text
        data["presentation"] = dict(self.presentation)
        return data

    @classmethod
    def _from_dict(cls, data):
        # v3: speaker_id
        # v2: speaker (конвертируем через slugify)
        speaker_id = data.get("speaker_id", "")

        if not speaker_id:
            old_speaker = data.get("speaker", "")
            if old_speaker:
                # Ленивый импорт — обходим цикл model <-> io
                try:
                    from ..io.storage import _slugify
                    speaker_id = _slugify(old_speaker)
                except Exception:
                    speaker_id = ""

        presentation_raw = data.get("presentation", {})

        if presentation_raw is None:
            presentation_raw = {}
        elif not isinstance(presentation_raw, dict):
            presentation_raw = {}

        return cls(
            node_id=data["id"],
            speaker_id=speaker_id,
            text=data.get("text", ""),
            presentation=presentation_raw,
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
        )


class ChoiceOption:
    """Один вариант выбора внутри ChoiceNode."""

    def __init__(
        self,
        option_id,
        text="",
        order=0,
        conditions=None,
        effects=None,
        is_default=False,
    ):
        self.id = option_id
        self.text = text
        self.order = int(order)

        # Архитектурный контракт v3:
        #   conditions = None | {"logic": "AND"|"OR", "items": [Condition...]}
        #   effects = [Effect...]
        #   is_default — fallback вариант, если остальные недоступны
        self.conditions = conditions
        self.effects = list(effects) if effects else []
        self.is_default = bool(is_default)

    def to_dict(self):
        return {
            "id": self.id,
            "text": self.text,
            "order": self.order,
            "conditions": self.conditions,
            "effects": list(self.effects),
            "is_default": self.is_default,
        }

    @classmethod
    def from_dict(cls, data):
        # Проверка типов для известных полей (forward compat с защитой)
        effects_raw = data.get("effects", [])
        if effects_raw is None:
            effects_raw = []
        elif not isinstance(effects_raw, list):
            effects_raw = []

        # conditions: приоритет v3, fallback на v2 (condition)
        conditions = data.get("conditions")
        if conditions is None and "condition" in data:
            old_cond = data.get("condition")
            # v2 condition=None → v3 conditions=None
            # v2 condition=<dict> → v3 conditions=<dict>
            conditions = old_cond

        # Защита: если conditions пришёл не dict и не None — сбрасываем
        if conditions is not None and not isinstance(conditions, dict):
            conditions = None

        is_default = bool(data.get("is_default", False))

        return cls(
            option_id=data["id"],
            text=data.get("text", ""),
            order=data.get("order", 0),
            conditions=conditions,
            effects=effects_raw,
            is_default=is_default,
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

    # Архитектурный контракт v3:
    #   outcome_type == "return_to_game" → вернуть управление в игру
    #   outcome_type == "start_dialogue" → запустить другой диалог
    #
    # outcome_id — метка для Unity (vasilisa_left, secret_revealed)
    # target_dialogue_id — используется только при start_dialogue
    VALID_OUTCOME_TYPES = ("return_to_game", "start_dialogue")

    def __init__(
        self,
        node_id,
        outcome_type="return_to_game",
        outcome_id=None,
        target_dialogue_id=None,
        x=0.0,
        y=0.0,
    ):
        super().__init__(node_id, x, y)

        if outcome_type not in self.VALID_OUTCOME_TYPES:
            outcome_type = "return_to_game"

        self.outcome_type = outcome_type
        self.outcome_id = outcome_id
        self.target_dialogue_id = target_dialogue_id

    def get_input_ports(self):
        return ["input"]

    def get_output_ports(self):
        return []

    def to_dict(self):
        data = super().to_dict()
        data["outcome_type"] = self.outcome_type
        data["outcome_id"] = self.outcome_id
        data["target_dialogue_id"] = self.target_dialogue_id
        return data

    @classmethod
    def _from_dict(cls, data):
        # v3: outcome_type
        # v2: outcome ("end"/"dialogue")
        outcome_type = data.get("outcome_type", "")

        if not outcome_type:
            old_outcome = data.get("outcome", "end")
            if old_outcome == "dialogue":
                outcome_type = "start_dialogue"
            else:
                outcome_type = "return_to_game"

        if outcome_type not in cls.VALID_OUTCOME_TYPES:
            outcome_type = "return_to_game"

        outcome_id = data.get("outcome_id")
        target = data.get("target_dialogue_id")

        # Защита от несоответствия: return_to_game не имеет target
        if outcome_type == "return_to_game":
            target = None

        return cls(
            node_id=data["id"],
            outcome_type=outcome_type,
            outcome_id=outcome_id,
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
