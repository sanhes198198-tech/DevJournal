"""
Генерация уникальных идентификаторов для модуля диалогов.

Отдельный модуль, независимый от cards/card_ids.py.
Технически UUID одинаковый, но семантически — свой.
"""

import uuid


def generate_dialogue_id():
    """Создаёт новый уникальный ID диалога."""
    return str(uuid.uuid4())


def generate_node_id():
    """Создаёт новый уникальный ID узла диалога."""
    return str(uuid.uuid4())


def generate_connection_id():
    """Создаёт новый уникальный ID связи между узлами."""
    return str(uuid.uuid4())


def generate_option_id():
    """Создаёт новый уникальный ID варианта выбора (ChoiceOption)."""
    return str(uuid.uuid4())
