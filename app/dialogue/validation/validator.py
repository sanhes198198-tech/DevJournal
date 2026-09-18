"""
Валидатор диалогового графа.

Проверяет структуру и выдаёт список проблем.
Ошибки и предупреждения разделены.

ВАЖНО: Save не блокируется валидатором.
Валидатор — только для информирования пользователя.
"""

from ..model import (
    Dialogue,
    StartNode,
    ReplyNode,
    ChoiceNode,
    EndNode,
)


# =========================================================
# КОНСТАНТЫ УРОВНЕЙ
# =========================================================

LEVEL_ERROR = "error"
LEVEL_WARNING = "warning"


# =========================================================
# ISSUE
# =========================================================

class ValidationIssue:
    """Одна проблема валидации."""

    def __init__(self, level, code, message, node_id=None, connection_id=None):
        self.level = level
        self.code = code
        self.message = message
        self.node_id = node_id
        self.connection_id = connection_id

    def __repr__(self):
        marker = "ERR" if self.level == LEVEL_ERROR else "WRN"
        return f"[{marker}] {self.code}: {self.message}"

    def to_dict(self):
        return {
            "level": self.level,
            "code": self.code,
            "message": self.message,
            "node_id": self.node_id,
            "connection_id": self.connection_id,
        }


# =========================================================
# RESULT
# =========================================================

class ValidationResult:
    """Результат валидации диалога."""

    def __init__(self):
        self.issues = []

    def add(self, issue):
        self.issues.append(issue)

    def add_error(self, code, message, node_id=None, connection_id=None):
        self.add(ValidationIssue(
            LEVEL_ERROR, code, message, node_id, connection_id,
        ))

    def add_warning(self, code, message, node_id=None, connection_id=None):
        self.add(ValidationIssue(
            LEVEL_WARNING, code, message, node_id, connection_id,
        ))

    def has_errors(self):
        return any(i.level == LEVEL_ERROR for i in self.issues)

    def has_warnings(self):
        return any(i.level == LEVEL_WARNING for i in self.issues)

    def errors(self):
        return [i for i in self.issues if i.level == LEVEL_ERROR]

    def warnings(self):
        return [i for i in self.issues if i.level == LEVEL_WARNING]

    def is_ok(self):
        return not self.has_errors()

    def __repr__(self):
        return (
            f"<ValidationResult errors={len(self.errors())} "
            f"warnings={len(self.warnings())}>"
        )


# =========================================================
# ГРАФОВЫЕ АЛГОРИТМЫ
# =========================================================

def find_reachable_nodes(dialogue):
    """
    BFS от StartNode.

    Возвращает set из node_id, достижимых от старта.
    Если StartNode нет — возвращает пустой set.
    """
    starts = [n for n in dialogue.nodes.values() if isinstance(n, StartNode)]

    if not starts:
        return set()

    # Строим карту исходящих связей: node_id -> list[target_node_id]
    outgoing = {}
    for c in dialogue.connections:
        outgoing.setdefault(c.source_node_id, []).append(c.target_node_id)

    visited = set()
    queue = [starts[0].id]

    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        for target in outgoing.get(current, []):
            if target not in visited:
                queue.append(target)

    return visited


def find_cycles(dialogue):
    """
    Ищет циклы через DFS.

    Возвращает список циклов (каждый — список node_id).
    Для упрощения возвращает только простые циклы.
    """
    # Строим карту исходящих связей
    outgoing = {}
    for c in dialogue.connections:
        outgoing.setdefault(c.source_node_id, []).append(c.target_node_id)

    visited = set()
    on_stack = set()
    stack = []
    cycles = []

    def dfs(node_id):
        if node_id in on_stack:
            # Нашли цикл — извлекаем его из stack
            try:
                start_idx = stack.index(node_id)
                cycle = stack[start_idx:] + [node_id]
                cycles.append(cycle)
            except ValueError:
                pass
            return

        if node_id in visited:
            return

        visited.add(node_id)
        on_stack.add(node_id)
        stack.append(node_id)

        for target in outgoing.get(node_id, []):
            dfs(target)

        stack.pop()
        on_stack.discard(node_id)

    for node_id in dialogue.nodes:
        if node_id not in visited:
            dfs(node_id)

    return cycles


# =========================================================
# ПРОВЕРКИ
# =========================================================

def _check_start_end(dialogue, result):
    """Проверка наличия Start / End и их количества."""
    starts = []
    ends = []

    for node in dialogue.nodes.values():
        if isinstance(node, StartNode):
            starts.append(node)
        elif isinstance(node, EndNode):
            ends.append(node)

    if not starts:
        result.add_error(
            "NO_START",
            "В диалоге нет StartNode.",
        )
    elif len(starts) > 1:
        result.add_error(
            "MULTIPLE_START",
            f"Найдено несколько StartNode: {len(starts)}.",
        )

    if not ends:
        result.add_warning(
            "NO_END",
            "В диалоге нет EndNode.",
        )


def _check_connections(dialogue, result):
    """Проверка связей: битые ссылки, дубликаты, невалидные порты."""

    seen_full = set()        # (source, source_port, target, target_port)
    seen_outputs = {}        # (source, source_port) -> connection_id

    for c in dialogue.connections:

        # --- Source / Target существуют ---
        src_node = dialogue.get_node(c.source_node_id)
        tgt_node = dialogue.get_node(c.target_node_id)

        if src_node is None:
            result.add_error(
                "MISSING_NODE_REF",
                f"Connection ссылается на несуществующий source: {c.source_node_id!r}",
                connection_id=c.id,
            )
            continue

        if tgt_node is None:
            result.add_error(
                "MISSING_NODE_REF",
                f"Connection ссылается на несуществующий target: {c.target_node_id!r}",
                connection_id=c.id,
            )
            continue

        # --- Порты существуют ---
        if c.source_port not in src_node.get_output_ports():
            result.add_error(
                "INVALID_PORT",
                f"У узла {src_node.id!r} нет output-порта {c.source_port!r}.",
                node_id=src_node.id,
                connection_id=c.id,
            )

        if c.target_port not in tgt_node.get_input_ports():
            result.add_error(
                "INVALID_PORT",
                f"У узла {tgt_node.id!r} нет input-порта {c.target_port!r}.",
                node_id=tgt_node.id,
                connection_id=c.id,
            )

        # --- Дубликат связи ---
        full_key = (c.source_node_id, c.source_port, c.target_node_id, c.target_port)
        if full_key in seen_full:
            result.add_error(
                "DUPLICATE_CONNECTION",
                f"Дубликат связи: {c.source_node_id}:{c.source_port} -> "
                f"{c.target_node_id}:{c.target_port}.",
                connection_id=c.id,
            )
        else:
            seen_full.add(full_key)

        # --- Один output = одна связь ---
        output_key = (c.source_node_id, c.source_port)
        if output_key in seen_outputs:
            result.add_error(
                "DUPLICATE_OUTPUT",
                f"У узла {c.source_node_id!r} порт {c.source_port!r} "
                f"имеет больше одной исходящей связи.",
                node_id=c.source_node_id,
                connection_id=c.id,
            )
        else:
            seen_outputs[output_key] = c.id


def _check_unreachable(dialogue, result):
    """Проверка недостижимых узлов."""
    starts = [n for n in dialogue.nodes.values() if isinstance(n, StartNode)]

    if not starts:
        # Нет смысла проверять — уже есть NO_START
        return

    reachable = find_reachable_nodes(dialogue)

    for node in dialogue.nodes.values():
        if node.id not in reachable:
            result.add_warning(
                "UNREACHABLE_NODE",
                f"Узел {node.id!r} ({node.type}) недостижим из Start.",
                node_id=node.id,
            )


def _check_choice_nodes(dialogue, result):
    """Проверка ChoiceNode: пустой и/или без связей."""
    for node in dialogue.nodes.values():
        if not isinstance(node, ChoiceNode):
            continue

        if not node.options:
            result.add_warning(
                "EMPTY_CHOICE",
                f"ChoiceNode {node.id!r} не имеет вариантов.",
                node_id=node.id,
            )
            continue

        # Проверяем, что у каждого option есть связь
        for opt in node.options:
            port = f"opt_{opt.id}"
            found = dialogue.find_connection(node.id, port)
            if found is None:
                result.add_warning(
                    "CHOICE_OPTION_WITHOUT_LINK",
                    f"ChoiceNode {node.id!r}: вариант {opt.text!r} "
                    f"не имеет связи.",
                    node_id=node.id,
                )


def _check_cycles(dialogue, result):
    """Проверка циклов — WARNING, не ERROR."""
    cycles = find_cycles(dialogue)

    for cycle in cycles:
        # Ограничиваем вывод, чтобы не заспамить
        if len(cycle) > 10:
            path = " -> ".join(cycle[:10]) + " -> ..."
        else:
            path = " -> ".join(cycle)

        result.add_warning(
            "CYCLE_DETECTED",
            f"Обнаружен цикл: {path}",
        )


# =========================================================
# END OUTCOME
# =========================================================

def _check_end_outcomes(dialogue, result, known_dialogue_ids=None):
    """
    Проверка корректности outcome у EndNode.

    known_dialogue_ids — опциональный set из известных ID диалогов.
    Если не передан — cross-dialogue проверка пропускается.
    """
    current_id = getattr(dialogue, "id", None)

    for node in dialogue.nodes.values():
        if not isinstance(node, EndNode):
            continue

        outcome = getattr(node, "outcome", "end")
        target = getattr(node, "target_dialogue_id", None)

        # --- outcome="end", но target указан ---
        if outcome == "end" and target is not None:
            result.add_error(
                "END_OUTCOME_MISMATCH",
                f"EndNode {node.id!r}: outcome='end', "
                f"но target_dialogue_id={target!r} указан.",
                node_id=node.id,
            )
            continue

        # --- outcome="dialogue", но target отсутствует ---
        if outcome == "dialogue" and not target:
            result.add_error(
                "END_OUTCOME_MISSING_TARGET",
                f"EndNode {node.id!r}: outcome='dialogue', "
                f"но target_dialogue_id не указан.",
                node_id=node.id,
            )
            continue

        # --- outcome="dialogue" и target указывает на себя ---
        if outcome == "dialogue" and target == current_id:
            result.add_warning(
                "END_OUTCOME_SELF_TARGET",
                f"EndNode {node.id!r}: диалог ссылается сам на себя.",
                node_id=node.id,
            )

        # --- outcome="dialogue", target не в known_dialogue_ids ---
        if (
            outcome == "dialogue"
            and known_dialogue_ids is not None
            and target
            and target not in known_dialogue_ids
        ):
            result.add_warning(
                "END_OUTCOME_UNKNOWN_TARGET",
                f"EndNode {node.id!r}: target_dialogue_id={target!r} "
                f"не найден среди известных диалогов проекта.",
                node_id=node.id,
            )


# =========================================================
# ГЛАВНАЯ ФУНКЦИЯ
# =========================================================

def validate_dialogue(dialogue, known_dialogue_ids=None):
    """
    Валидирует диалог.

    Параметры:
        dialogue — Dialogue
        known_dialogue_ids — опциональный set/list ID диалогов проекта.
            Если передан — проверяется, что outcome="dialogue"
            указывает на существующий диалог.

    Возвращает ValidationResult со списком issue.
    """
    result = ValidationResult()

    if dialogue is None:
        result.add_error("NULL_DIALOGUE", "Dialogue is None.")
        return result

    _check_start_end(dialogue, result)
    _check_connections(dialogue, result)
    _check_unreachable(dialogue, result)
    _check_choice_nodes(dialogue, result)
    _check_cycles(dialogue, result)
    _check_end_outcomes(dialogue, result, known_dialogue_ids)

    return result
