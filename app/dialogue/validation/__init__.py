"""
Validation layer для модуля диалогов.

Проверяет структуру графа и возвращает список проблем.
"""

from .validator import (
    LEVEL_ERROR,
    LEVEL_WARNING,
    ValidationIssue,
    ValidationResult,
    validate_dialogue,
    find_reachable_nodes,
    find_cycles,
)


__all__ = [
    "LEVEL_ERROR",
    "LEVEL_WARNING",
    "ValidationIssue",
    "ValidationResult",
    "validate_dialogue",
    "find_reachable_nodes",
    "find_cycles",
]
