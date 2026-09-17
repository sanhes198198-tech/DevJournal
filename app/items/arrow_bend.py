from __future__ import annotations

import math

from PySide6.QtCore import QPointF


class ArrowBendController:
    """
    Логика контрольной точки изгиба стрелки.

    Контроллер не рисует стрелку и не изменяет QGraphicsItem.
    Он отвечает только за математическую часть:

    - начальную позицию контрольной точки;
    - её положение относительно прямой стрелки;
    - расчёт изгиба;
    - определение направления и силы изгиба.
    """

    def __init__(
        self,
        bend_ratio=0.5,
        max_offset=1000.0,
    ):
        self.bend_ratio = float(
            bend_ratio
        )

        self.max_offset = float(
            max_offset
        )

        self._offset = 0.0

    # ============================================================
    # CONTROL POINT
    # ============================================================

    def control_point(
        self,
        start,
        end,
    ):
        """
        Возвращает положение контрольной точки.

        При offset == 0 точка находится точно
        в середине прямой между start и end.

        Положительное значение offset
        изгибает стрелку в одну сторону.

        Отрицательное значение offset
        изгибает стрелку в противоположную сторону.
        """

        start = QPointF(start)
        end = QPointF(end)

        dx = (
            end.x()
            - start.x()
        )

        dy = (
            end.y()
            - start.y()
        )

        length = math.sqrt(
            dx * dx
            +
            dy * dy
        )

        if length <= 0.0001:
            return QPointF(start)

        center_x = (
            start.x()
            +
            dx * self.bend_ratio
        )

        center_y = (
            start.y()
            +
            dy * self.bend_ratio
        )

        perpendicular_x = (
            -dy / length
        )

        perpendicular_y = (
            dx / length
        )

        offset = max(
            -self.max_offset,
            min(
                self.max_offset,
                self._offset,
            ),
        )

        return QPointF(
            center_x
            +
            perpendicular_x
            * offset,

            center_y
            +
            perpendicular_y
            * offset,
        )

    # ============================================================
    # OFFSET
    # ============================================================

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, value):
        try:
            value = float(value)
        except (
            TypeError,
            ValueError,
        ):
            value = 0.0

        self._offset = max(
            -self.max_offset,
            min(
                self.max_offset,
                value,
            ),
        )

    # ============================================================
    # MOUSE POSITION → OFFSET
    # ============================================================

    def offset_from_point(
        self,
        start,
        end,
        point,
    ):
        """
        Вычисляет величину изгиба по позиции мыши.

        Точка мыши проецируется на перпендикуляр
        относительно центральной точки стрелки.

        Таким образом:

        мышь выше прямой
            → стрелка гнётся вверх

        мышь ниже прямой
            → стрелка гнётся вниз
        """

        start = QPointF(start)
        end = QPointF(end)
        point = QPointF(point)

        dx = (
            end.x()
            - start.x()
        )

        dy = (
            end.y()
            - start.y()
        )

        length = math.sqrt(
            dx * dx
            +
            dy * dy
        )

        if length <= 0.0001:
            return 0.0

        center_x = (
            start.x()
            +
            dx * self.bend_ratio
        )

        center_y = (
            start.y()
            +
            dy * self.bend_ratio
        )

        relative_x = (
            point.x()
            - center_x
        )

        relative_y = (
            point.y()
            - center_y
        )

        perpendicular_x = (
            -dy / length
        )

        perpendicular_y = (
            dx / length
        )

        offset = (
            relative_x
            * perpendicular_x
            +
            relative_y
            * perpendicular_y
        )

        return max(
            -self.max_offset,
            min(
                self.max_offset,
                offset,
            ),
        )

    # ============================================================
    # RESET
    # ============================================================

    def reset(self):
        """
        Возвращает стрелку в прямое состояние.
        """

        self._offset = 0.0

    # ============================================================
    # IS BENT
    # ============================================================

    def is_bent(self):
        """
        Проверяет, есть ли у стрелки изгиб.
        """

        return abs(
            self._offset
        ) > 0.0001