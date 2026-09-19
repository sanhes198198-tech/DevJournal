"""
Команды редактирования архитектурного документа.

Все команды меняют ТОЛЬКО Document. Scene реагирует через
сигналы element_added / element_removed / element_changed.
"""

from .add_element import AddElementCommand
from .remove_element import DeleteElementCommand
from .modify_element import ModifyElementCommand

__all__ = [
    "AddElementCommand",
    "DeleteElementCommand",
    "ModifyElementCommand",
]
