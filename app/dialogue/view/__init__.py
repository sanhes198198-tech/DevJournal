"""
View layer для модуля диалогов.

Qt-часть: сцена, виджет, визуальные узлы и связи, инспектор.
"""

from .port_item import PortItem
from .node_item import DialogueNodeItem
from .connection_item import DialogueConnectionItem
from .scene import DialogueScene
from .view import DialogueView
from .inspector import DialogueInspector


__all__ = [
    "PortItem",
    "DialogueNodeItem",
    "DialogueConnectionItem",
    "DialogueScene",
    "DialogueView",
    "DialogueInspector",
]
