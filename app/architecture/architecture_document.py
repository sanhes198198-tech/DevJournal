"""
ArchitectureDocument — обёртка модель + путь + флаг modified.

Слой между редактором и моделью. Редактор не должен знать,
откуда пришла модель и сохранена ли она.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from .model.architecture import ArchitectureModel
from .io import storage


class ArchitectureDocument(QObject):
    """Документ архитектуры.

    Сигналы:
        modified_changed(bool) — при смене флага modified
    """

    modified_changed = Signal(bool)

    element_added = Signal(str)      # element_id
    element_removed = Signal(str)    # element_id
    element_changed = Signal(str)    # element_id

    def __init__(
        self,
        path: Path | None,
        model: ArchitectureModel,
        modified: bool = False,
        parent=None,
    ):
        super().__init__(parent)

        self._path = Path(path) if path else None
        self._model = model
        self._modified = modified

    # --- фабрики ---

    @classmethod
    def create_new(
        cls,
        path: Path,
        name: str = "Архитектура",
    ) -> "ArchitectureDocument":
        """Новый пустой документ. Файл на диск не пишется."""
        model = ArchitectureModel.create_empty(name=name)
        return cls(path=path, model=model, modified=True)

    @classmethod
    def load(cls, path: Path) -> "ArchitectureDocument":
        """Загрузка с диска. Кидает StorageError при проблеме."""
        model = storage.load_model(path)
        return cls(path=path, model=model, modified=False)

    # --- API ---

    @property
    def model(self) -> ArchitectureModel:
        return self._model

    @property
    def path(self) -> Path | None:
        return self._path

    def is_modified(self) -> bool:
        return self._modified

    def mark_modified(self) -> None:
        if not self._modified:
            self._modified = True
            self.modified_changed.emit(True)

    def mark_saved(self) -> None:
        if self._modified:
            self._modified = False
            self.modified_changed.emit(False)

    # ============================================================
    # ЭЛЕМЕНТЫ
    # ============================================================

    def add_element(self, element) -> None:
        """Добавляет элемент. Эмитит element_added."""
        self._model.add_element(element)
        self.mark_modified()
        self.element_added.emit(element.id)

    def remove_element(self, element_id: str) -> None:
        """Удаляет элемент. Эмитит element_removed.

        Если элемента нет — тихо ничего не делает.
        """
        removed = self._model.remove_element(element_id)
        if removed is None:
            return
        self.mark_modified()
        self.element_removed.emit(element_id)

    def update_element(self, element_id: str, **fields) -> None:
        """Обновляет поля элемента.

        Защита:
          - элемент существует
          - поле существует у элемента
          - id и type не изменяемы
        """
        el = self._model.get_element(element_id)
        if el is None:
            raise ValueError(f"Element {element_id!r} not found")

        PROTECTED = {"id", "type"}

        for key in fields:
            if key in PROTECTED:
                raise AttributeError(
                    f"Cannot modify protected field {key!r}"
                )
            if not hasattr(el, key):
                raise AttributeError(
                    f"Element {element_id!r} has no field {key!r}"
                )

        changed = False
        for key, value in fields.items():
            if getattr(el, key) != value:
                setattr(el, key, value)
                changed = True

        if changed:
            self.mark_modified()
            self.element_changed.emit(element_id)

    # ============================================================
    # СОХРАНЕНИЕ
    # ============================================================

    def save(self) -> None:
        """Сохраняет модель на диск. Кидает StorageError при проблеме."""
        if self._path is None:
            raise storage.StorageError("Не задан путь для сохранения")

        self._model.touch_modified()
        storage.save_model(self._model, self._path)
        self.mark_saved()
