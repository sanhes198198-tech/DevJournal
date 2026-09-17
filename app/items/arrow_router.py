from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF


class ArrowRouter:
    """
    Маршрутизатор прямых стрелок.

    Стрелка всегда строится по прямой между двумя карточками.

    Если прямая проходит через другие карточки,
    она не пытается их обходить.
    Карточки находятся выше стрелки по Z-порядку
    и визуально перекрывают участок стрелки.

    Маршрутизатор отвечает только за:
    - получение границ карточек;
    - определение точки входа и выхода;
    - построение прямого маршрута.

    Он не изменяет карточки и не управляет
    жизненным циклом стрелок.
    """

    CLEARANCE = 0.0

    def __init__(
        self,
        grid_size: float = 20.0,
        clearance: float = CLEARANCE,
    ):
        self.grid_size = float(grid_size)
        self.clearance = float(clearance)

    # ============================================================
    # PUBLIC API
    # ============================================================

    def route(
        self,
        source_item,
        target_item,
        obstacles=None,
    ):
        """
        Возвращает прямой маршрут между двумя карточками.

        Формат:

            [start, end]

        start находится на границе исходной карточки.

        end находится на границе целевой карточки.

        Другие карточки не считаются препятствиями.
        Если линия проходит через них, они должны
        визуально перекрывать стрелку.
        """

        if source_item is None:
            return []

        if target_item is None:
            return []

        source_rect = self._item_scene_rect(
            source_item
        )

        target_rect = self._item_scene_rect(
            target_item
        )

        if source_rect is None:
            return []

        if target_rect is None:
            return []

        source_center = source_rect.center()
        target_center = target_rect.center()

        start = self._border_point(
            source_rect,
            target_center,
        )

        end = self._border_point(
            target_rect,
            source_center,
        )

        return [
            start,
            end,
        ]

    # ============================================================
    # ITEM GEOMETRY
    # ============================================================

    def _item_scene_rect(
        self,
        item,
    ):
        """
        Получает boundingRect объекта
        в координатах сцены.
        """

        try:
            rect = item.sceneBoundingRect()

        except RuntimeError:
            return None

        except AttributeError:
            return None

        except Exception:
            return None

        if rect is None:
            return None

        if rect.isEmpty():
            return None

        return QRectF(
            rect
        )

    # ============================================================
    # BORDER POINT
    # ============================================================

    def _border_point(
        self,
        rect: QRectF,
        target: QPointF,
    ):
        """
        Находит точку на границе прямоугольной карточки,
        направленную в сторону target.

        Благодаря этому стрелка соединяется
        с границей карточки, а не с её центром.
        """

        center = rect.center()

        dx = (
            target.x()
            - center.x()
        )

        dy = (
            target.y()
            - center.y()
        )

        # ----------------------------------------------------
        # Центры практически совпали.
        # Используем нижнюю границу как безопасный
        # запасной вариант.
        # ----------------------------------------------------

        if (
            abs(dx) < 0.0001
            and
            abs(dy) < 0.0001
        ):
            return QPointF(
                center.x(),
                rect.bottom(),
            )

        half_width = (
            rect.width()
            / 2.0
        )

        half_height = (
            rect.height()
            / 2.0
        )

        # ----------------------------------------------------
        # Определяем, какая сторона прямоугольника
        # пересекается лучом от центра к target.
        # ----------------------------------------------------

        if abs(dx) > 0.0001:
            scale_x = (
                half_width
                / abs(dx)
            )

        else:
            scale_x = float("inf")

        if abs(dy) > 0.0001:
            scale_y = (
                half_height
                / abs(dy)
            )

        else:
            scale_y = float("inf")

        scale = min(
            scale_x,
            scale_y,
        )

        x = (
            center.x()
            + dx * scale
        )

        y = (
            center.y()
            + dy * scale
        )

        # ----------------------------------------------------
        # Небольшой зазор от края карточки.
        #
        # Сейчас CLEARANCE = 0,
        # поэтому соединение идёт непосредственно
        # к границе карточки.
        # ----------------------------------------------------

        if self.clearance > 0.0:
            length = (
                dx * dx
                +
                dy * dy
            ) ** 0.5

            if length > 0.0001:
                offset_x = (
                    dx / length
                    * self.clearance
                )

                offset_y = (
                    dy / length
                    * self.clearance
                )

                x += offset_x
                y += offset_y

        return QPointF(
            x,
            y,
        )

    # ============================================================
    # COMPATIBILITY HELPERS
    # ============================================================
    #
    # Эти методы оставлены как отдельные безопасные
    # вспомогательные точки API, чтобы существующий код
    # проекта не ломался при обращении к ArrowRouter.
    #
    # Они больше не участвуют в поиске маршрута.
    # ============================================================

    def _looks_like_card(
        self,
        item,
    ):
        """
        Проверяет, похож ли объект на карточку.
        """

        if item is None:
            return False

        try:
            return hasattr(
                item,
                "arrows",
            )

        except Exception:
            return False

    def _collect_obstacles(
        self,
        source_item,
        target_item,
        obstacles,
    ):
        """
        Возвращает пустой список препятствий.

        В новой модели карточки не являются
        препятствиями для маршрутизатора.

        Они просто рисуются поверх стрелки.
        """

        return []

    def _segment_hits_obstacles(
        self,
        start,
        end,
        obstacles,
    ):
        """
        В новой системе пересечение с карточками
        не является ошибкой маршрута.
        """

        return False