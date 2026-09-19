"""
ArchScene — QGraphicsScene архитектурного редактора.

Координатная система сцены: метры.
Направление Y: вниз (Qt-нативно).

Модель использует Y↑ (архитектурно). Конвертация:
    scene_y = -model_y

Выполняется в момент размещения items (в M1+).
В M0 items нет — только сетка, которая живёт в Qt-системе.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtWidgets import QGraphicsScene

from .grid import GridLayer


# Огромный scene rect: ±1000 метров.
# Авто-расширение Qt не работает, пока нет items.
SCENE_HALF = 1000.0
SCENE_RECT = QRectF(-SCENE_HALF, -SCENE_HALF, SCENE_HALF * 2, SCENE_HALF * 2)


class ArchScene(QGraphicsScene):
    """Сцена архитектурного редактора."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Сцена в метрах
        self.setSceneRect(SCENE_RECT)

        # Сетка
        self._grid = GridLayer()

        # Фон (позади сетки)
        self.setBackgroundBrush(self._make_background_brush())

    # ------------------------------------------------------------

    def drawBackground(self, painter, rect: QRectF) -> None:
        """Рисует фон и сетку.

        rect — видимая область сцены в метрах.
        ppm — pixels per meter, из текущего transform view.
        """
        super().drawBackground(painter, rect)

        # Найти ppm. У сцены может быть несколько view (у нас одно).
        ppm = 50.0  # fallback
        views = self.views()
        if views:
            transform = views[0].transform()
            ppm = abs(transform.m11())

        self._grid.draw(painter, rect, ppm)

    def drawForeground(self, painter, rect: QRectF) -> None:
        """Зарезервировано для будущих overlays (snap, selection)."""
        super().drawForeground(painter, rect)
        # M0: пусто

    # ------------------------------------------------------------

    @staticmethod
    def _make_background_brush():
        from PySide6.QtGui import QBrush, QColor
        return QBrush(QColor("#181818"))
