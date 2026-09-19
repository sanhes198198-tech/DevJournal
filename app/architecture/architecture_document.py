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

    def save(self) -> None:
        """Сохраняет модель на диск. Кидает StorageError при проблеме."""
        if self._path is None:
            raise storage.StorageError("Не задан путь для сохранения")

        self._model.touch_modified()
        storage.save_model(self._model, self._path)
        self.mark_saved()
