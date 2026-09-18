"""
QUndoCommand-классы для редактора диалогов.

Принципы:
- UI никогда не мутирует модель напрямую.
- Все изменения — через stack.push(Command(...)).
- undo() восстанавливает исходное состояние, включая ID.
- redo() — идемпотентна (при создании QUndoCommand Qt сразу вызывает redo).
"""

from PySide6.QtGui import QUndoCommand


# =========================================================
# CHANGE PROPERTY (speaker / text / question)
# =========================================================

class ChangePropertyCommand(QUndoCommand):
    """
    Изменение одного поля модели.

    Для текстовых полей соседние команды с одинаковым
    (target_id, prop_name) автоматически merge-ятся,
    чтобы Ctrl+Z отменял не по одному символу.
    """

    def __init__(self, target, prop_name, old_value, new_value, notify=None):
        super().__init__(f"Change {prop_name}")

        self.target = target
        self.prop_name = prop_name
        self.old_value = old_value
        self.new_value = new_value
        self.notify = notify

        # Первый redo не должен менять модель,
        # если UI уже поменял её до push (для merge).
        # Но по нашему принципу — UI не меняет модель.
        # Значит redo всегда применяет new_value.
        self._skip_first_redo = False

    def id(self):
        """
        Для merge — уникальный ключ (target + field).

        ВАЖНО: Qt ждёт 32-битный signed int,
        поэтому обрезаем hash до 31 бита (0x7FFFFFFF).
        """
        h = hash((id(self.target), self.prop_name))
        return h & 0x7FFFFFFF

    def mergeWith(self, other):
        """Склеиваем два последовательных изменения одного поля."""
        if not isinstance(other, ChangePropertyCommand):
            return False
        if self.target is not other.target:
            return False
        if self.prop_name != other.prop_name:
            return False

        self.new_value = other.new_value
        return True

    def redo(self):
        setattr(self.target, self.prop_name, self.new_value)
        if callable(self.notify):
            try:
                self.notify()
            except Exception:
                pass

    def undo(self):
        setattr(self.target, self.prop_name, self.old_value)
        if callable(self.notify):
            try:
                self.notify()
            except Exception:
                pass


# =========================================================
# MOVE NODE
# =========================================================

class MoveNodeCommand(QUndoCommand):
    """Перемещение узла из old_pos в new_pos."""

    def __init__(self, node, old_pos, new_pos, notify=None):
        super().__init__("Move node")

        self.node = node
        self.old_pos = (float(old_pos[0]), float(old_pos[1]))
        self.new_pos = (float(new_pos[0]), float(new_pos[1]))
        self.notify = notify

    def redo(self):
        self.node.x = self.new_pos[0]
        self.node.y = self.new_pos[1]
        if callable(self.notify):
            try:
                self.notify()
            except Exception:
                pass

    def undo(self):
        self.node.x = self.old_pos[0]
        self.node.y = self.old_pos[1]
        if callable(self.notify):
            try:
                self.notify()
            except Exception:
                pass


# =========================================================
# CREATE / DELETE NODE
# =========================================================

class CreateNodeCommand(QUndoCommand):
    """Добавить узел в диалог."""

    def __init__(self, dialogue, node, notify=None):
        super().__init__(f"Create {node.type}")
        self.dialogue = dialogue
        self.node = node
        self.notify = notify

    def redo(self):
        self.dialogue.nodes[self.node.id] = self.node
        if callable(self.notify):
            try:
                self.notify()
            except Exception:
                pass

    def undo(self):
        self.dialogue.remove_node(self.node.id)
        if callable(self.notify):
            try:
                self.notify()
            except Exception:
                pass


class DeleteNodeCommand(QUndoCommand):
    """
    Удалить узел и ВСЕ его связи — одной atomic командой.

    При undo — восстанавливает узел и связи с теми же ID.
    """

    def __init__(self, dialogue, node, notify=None):
        super().__init__(f"Delete {node.type}")
        self.dialogue = dialogue
        self.node = node
        self.notify = notify

        # Заполняется в redo
        self.saved_connections = []
        self.saved_index = None

    def redo(self):
        # Сохраняем связи, которые будут удалены
        self.saved_connections = [
            c for c in self.dialogue.connections
            if c.source_node_id == self.node.id
            or c.target_node_id == self.node.id
        ]

        # Запоминаем позицию узла в списке? Узлы — dict, порядок неважен.
        self.dialogue.remove_node(self.node.id)

        if callable(self.notify):
            try:
                self.notify()
            except Exception:
                pass

    def undo(self):
        # Восстанавливаем узел
        self.dialogue.nodes[self.node.id] = self.node

        # Восстанавливаем связи (проверяем, чтобы не задвоить)
        existing_ids = {c.id for c in self.dialogue.connections}
        for c in self.saved_connections:
            if c.id not in existing_ids:
                self.dialogue.connections.append(c)

        if callable(self.notify):
            try:
                self.notify()
            except Exception:
                pass


# =========================================================
# CREATE / DELETE CONNECTION
# =========================================================

class CreateConnectionCommand(QUndoCommand):
    """Добавить связь."""

    def __init__(self, dialogue, connection, notify=None):
        super().__init__("Create connection")
        self.dialogue = dialogue
        self.connection = connection
        self.notify = notify

    def redo(self):
        self.dialogue.connections.append(self.connection)
        if callable(self.notify):
            try:
                self.notify()
            except Exception:
                pass

    def undo(self):
        self.dialogue.connections = [
            c for c in self.dialogue.connections
            if c.id != self.connection.id
        ]
        if callable(self.notify):
            try:
                self.notify()
            except Exception:
                pass


class DeleteConnectionCommand(QUndoCommand):
    """Удалить связь. При undo — восстанавливает на прежнем месте."""

    def __init__(self, dialogue, connection, notify=None):
        super().__init__("Delete connection")
        self.dialogue = dialogue
        self.connection = connection
        self.notify = notify
        self.saved_index = None

    def redo(self):
        for i, c in enumerate(self.dialogue.connections):
            if c.id == self.connection.id:
                self.saved_index = i
                self.dialogue.connections.pop(i)
                break

        if callable(self.notify):
            try:
                self.notify()
            except Exception:
                pass

    def undo(self):
        if self.saved_index is None:
            self.dialogue.connections.append(self.connection)
        else:
            self.dialogue.connections.insert(self.saved_index, self.connection)

        if callable(self.notify):
            try:
                self.notify()
            except Exception:
                pass


# =========================================================
# OPTIONS В CHOICE
# =========================================================

class AddOptionCommand(QUndoCommand):
    """Добавить ChoiceOption в ChoiceNode."""

    def __init__(self, node, option, notify=None):
        super().__init__("Add option")
        self.node = node
        self.option = option
        self.notify = notify

    def redo(self):
        if self.option not in self.node.options:
            self.node.options.append(self.option)
            self.node.sort_options()

        if callable(self.notify):
            try:
                self.notify()
            except Exception:
                pass

    def undo(self):
        self.node.remove_option(self.option.id)

        if callable(self.notify):
            try:
                self.notify()
            except Exception:
                pass


class RemoveOptionCommand(QUndoCommand):
    """
    Удалить ChoiceOption.

    ВАЖНО: команда НЕ трогает связи с другими узлами.
    Если у option была связь — она должна быть удалена
    отдельной командой (или макросом) на уровне UI.
    """

    def __init__(self, node, option, notify=None):
        super().__init__("Remove option")
        self.node = node
        self.option = option
        self.notify = notify

    def redo(self):
        self.node.remove_option(self.option.id)

        if callable(self.notify):
            try:
                self.notify()
            except Exception:
                pass

    def undo(self):
        if self.option not in self.node.options:
            self.node.options.append(self.option)
            self.node.sort_options()

        if callable(self.notify):
            try:
                self.notify()
            except Exception:
                pass


class MoveOptionCommand(QUndoCommand):
    """Поменять местами order двух соседних вариантов."""

    def __init__(self, node, option_a, option_b, notify=None):
        super().__init__("Move option")
        self.node = node
        self.option_a = option_a
        self.option_b = option_b
        self.notify = notify

    def redo(self):
        self.option_a.order, self.option_b.order = (
            self.option_b.order,
            self.option_a.order,
        )
        self.node.sort_options()

        if callable(self.notify):
            try:
                self.notify()
            except Exception:
                pass

    def undo(self):
        # Меняем обратно — операция симметричная
        self.option_a.order, self.option_b.order = (
            self.option_b.order,
            self.option_a.order,
        )
        self.node.sort_options()

        if callable(self.notify):
            try:
                self.notify()
            except Exception:
                pass
