"""
DeleteElementCommand — удаление элемента.

Элемент сохраняется внутри команды, чтобы undo мог его вернуть.
"""

from __future__ import annotations

from PySide6.QtGui import QUndoCommand


class DeleteElementCommand(QUndoCommand):
    """Команда: удалить элемент из документа."""

    def __init__(self, document, element, parent=None):
        super().__init__(
            f"Удалить «{getattr(element, 'name', element.type)}»",
            parent,
        )
        self._document = document
        self._element = element

    def redo(self) -> None:
        self._document.remove_element(self._element.id)

    def undo(self) -> None:
        self._document.add_element(self._element)
