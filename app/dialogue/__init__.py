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
    get_dialogues_dir,
    ensure_dialogues_dir,
    get_dialogue_path,
    get_index_path,
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
    DialogueInspector,
)

from .dialogue_list import DialogueList
from .dialogue_editor import DialogueEditorWindow

from .commands import (
    ChangePropertyCommand,
    MoveNodeCommand,
    CreateNodeCommand,
    DeleteNodeCommand,
    CreateConnectionCommand,
    DeleteConnectionCommand,
    AddOptionCommand,
    RemoveOptionCommand,
    MoveOptionCommand,
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
    "get_dialogues_dir",
    "ensure_dialogues_dir",
    "get_dialogue_path",
    "get_index_path",
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
    "DialogueInspector",
    # list
    "DialogueList",
    "DialogueEditorWindow",
    # commands
    "ChangePropertyCommand",
    "MoveNodeCommand",
    "CreateNodeCommand",
    "DeleteNodeCommand",
    "CreateConnectionCommand",
    "DeleteConnectionCommand",
    "AddOptionCommand",
    "RemoveOptionCommand",
    "MoveOptionCommand",
]
