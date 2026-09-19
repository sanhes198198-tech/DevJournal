"""
AddElementCommand — добавление элемента.
"""

from __future__ import annotations

from PySide6.QtGui import QUndoCommand


class AddElementCommand(QUndoCommand):
    """Команда: добавить элемент в документ."""

    def __init__(self, document, element, parent=None):
        super().__init__(
            f"Добавить «{getattr(element, 'name', element.type)}»",
            parent,
        )
        self._document = document
        self._element = element

    def redo(self) -> None:
        self._document.add_element(self._element)

    def undo(self) -> None:
        self._document.remove_element(self._element.id)
