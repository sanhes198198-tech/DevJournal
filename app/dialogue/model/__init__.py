"""
Model layer для модуля диалогов.

Чистая модель данных — не зависит от Qt.
"""

from .node import (
    DialogueNode,
    StartNode,
    ReplyNode,
    ChoiceNode,
    ChoiceOption,
    EndNode,
    NODE_TYPE_MAP,
    JumpNode,
    CallDialogueNode,
)

from .connection import DialogueConnection

from .dialogue import Dialogue


__all__ = [
    "DialogueNode",
    "StartNode",
    "ReplyNode",
    "ChoiceNode",
    "ChoiceOption",
    "EndNode",
    "NODE_TYPE_MAP",
    "DialogueConnection",
    "Dialogue",
    "JumpNode",
    "CallDialogueNode",
]
