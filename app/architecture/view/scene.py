"""
ArchScene — QGraphicsScene архитектурного редактора.

Подписывается на сигналы ArchitectureDocument и держит items_by_id
в синхроне с моделью.

Координаты сцены: метры. Y↓ (Qt нативно).
Модель: Y↑. Конвертация через view/coords.py.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtWidgets import QGraphicsScene

from ..model.room import Room
from .grid import GridLayer
from .items.room_item import RoomItem


SCENE_HALF = 1000.0
SCENE_RECT = QRectF(-SCENE_HALF, -SCENE_HALF, SCENE_HALF * 2, SCENE_HALF * 2)


class ArchScene(QGraphicsScene):
    """Сцена архитектурного редактора."""

    def __init__(self, document, parent=None):
        super().__init__(parent)

        self._document = document
        self._items_by_id: dict[str, RoomItem] = {}

        self.setSceneRect(SCENE_RECT)
        self._grid = GridLayer()
        self.setBackgroundBrush(self._make_background_brush())

        # Подписка на сигналы документа
        document.element_added.connect(self._on_element_added)
        document.element_removed.connect(self._on_element_removed)
        document.element_changed.connect(self._on_element_changed)

        # Заполнить из модели (если загружен существующий документ)
        self._populate_from_model()

    # ============================================================
    # ДОСТУП
    # ============================================================

    @property
    def document(self):
        return self._document

    def item_for(self, element_id: str) -> RoomItem | None:
        return self._items_by_id.get(element_id)

    # ============================================================
    # ЗАПОЛНЕНИЕ
    # ============================================================

    def _populate_from_model(self) -> None:
        for el in self._document.model.elements.values():
            self._create_item(el)

    def _create_item(self, element) -> RoomItem | None:
        """Создаёт item по элементу модели."""
        if isinstance(element, Room):
            item = RoomItem(element)
            self.addItem(item)
            self._items_by_id[element.id] = item
            return item
        # Другие типы — в M2+
        return None

    # ============================================================
    # СИГНАЛЫ ДОКУМЕНТА
    # ============================================================

    def _on_element_added(self, element_id: str) -> None:
        el = self._document.model.get_element(element_id)
        if el is None:
            return
        self._create_item(el)

    def _on_element_removed(self, element_id: str) -> None:
        item = self._items_by_id.pop(element_id, None)
        if item is not None:
            self.removeItem(item)

    def _on_element_changed(self, element_id: str) -> None:
        item = self._items_by_id.get(element_id)
        if item is not None:
            item.sync_from_model()

    # ============================================================
    # РИСОВАНИЕ
    # ============================================================

    def drawBackground(self, painter, rect: QRectF) -> None:
        super().drawBackground(painter, rect)

        ppm = 50.0
        views = self.views()
        if views:
            transform = views[0].transform()
            ppm = abs(transform.m11())

        self._grid.draw(painter, rect, ppm)

    def drawForeground(self, painter, rect: QRectF) -> None:
        super().drawForeground(painter, rect)
        # M0/M1b: пусто

    # ============================================================

    @staticmethod
    def _make_background_brush():
        from PySide6.QtGui import QBrush, QColor
        return QBrush(QColor("#181818"))
