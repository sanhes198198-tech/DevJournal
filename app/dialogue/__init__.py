"""
Модуль диалогов для DevJournal.

Независимая подсистема: своя модель данных, свой view,
своё сохранение, свой undo/redo.
"""

from .ids import (
    generate_dialogue_id,
    generate_node_id,
    generate_connection_id,
    generate_option_id,
)

from .model import (
    Dialogue,
    DialogueNode,
    DialogueConnection,
    StartNode,
    ReplyNode,
    ChoiceNode,
    ChoiceOption,
    EndNode,
    NODE_TYPE_MAP,
)

from .io import (
    DIALOGUES_DIR_NAME,
    INDEX_FILE_NAME,
    DIALOGUE_FORMAT_VERSION,
    save_dialogue,
    load_dialogue,
    dialogue_exists,
    delete_dialogue,
    list_dialogue_ids,
    default_index,
    save_index,
    load_index,
    rebuild_index,
)

from .validation import (
    LEVEL_ERROR,
    LEVEL_WARNING,
    ValidationIssue,
    ValidationResult,
    validate_dialogue,
)

from .view import (
    PortItem,
    DialogueNodeItem,
    DialogueConnectionItem,
    DialogueScene,
    DialogueView,
)


__all__ = [
    # ids
    "generate_dialogue_id",
    "generate_node_id",
    "generate_connection_id",
    "generate_option_id",
    # model
    "Dialogue",
    "DialogueNode",
    "DialogueConnection",
    "StartNode",
    "ReplyNode",
    "ChoiceNode",
    "ChoiceOption",
    "EndNode",
    "NODE_TYPE_MAP",
    # io
    "DIALOGUES_DIR_NAME",
    "INDEX_FILE_NAME",
    "DIALOGUE_FORMAT_VERSION",
    "save_dialogue",
    "load_dialogue",
    "dialogue_exists",
    "delete_dialogue",
    "list_dialogue_ids",
    "default_index",
    "save_index",
    "load_index",
    "rebuild_index",
    # validation
    "LEVEL_ERROR",
    "LEVEL_WARNING",
    "ValidationIssue",
    "ValidationResult",
    "validate_dialogue",
    # view
    "PortItem",
    "DialogueNodeItem",
    "DialogueConnectionItem",
    "DialogueScene",
    "DialogueView",
]
