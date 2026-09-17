from PySide6.QtCore import (
    Qt,
    QPointF,
    QRectF,
    QTimer,
)
from PySide6.QtGui import (
    QPainterPath,
    QPainterPathStroker,
    QPen,
    QBrush,
    QPolygonF,
    QColor,
)
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
)

from .arrow_item import ArrowItem
from .arrow_router import ArrowRouter
from .arrow_style import ArrowStyle
from .arrow_bend import ArrowBendController


class ArrowBendHandle(QGraphicsEllipseItem):
    """
    Контрольная точка изгиба стрелки.

    Кружок является отдельным графическим объектом
    и не вмешивается в существующую логику ArrowItem.
    """

    NORMAL_RADIUS = 5.0
    HOVER_RADIUS = 7.0

    NORMAL_COLOR = QColor("#FFFFFF")
    HOVER_COLOR = QColor("#000000")

    NORMAL_BORDER = QColor("#000000")
    HOVER_BORDER = QColor("#FFFFFF")

    HANDLE_Z = 10000.0

    def __init__(self, arrow):
        radius = self.NORMAL_RADIUS

        super().__init__(
            -radius,
            -radius,
            radius * 2.0,
            radius * 2.0,
        )

        self.arrow = arrow
        self._dragging = False

        self.setZValue(
            self.HANDLE_Z
        )

        self.setAcceptHoverEvents(
            True
        )

        self.setAcceptedMouseButtons(
            Qt.MouseButton.LeftButton
        )

        self.setPen(
            QPen(
                self.NORMAL_BORDER,
                1.5,
            )
        )

        self.setBrush(
            QBrush(
                self.NORMAL_COLOR
            )
        )

    # ============================================================
    # HOVER
    # ============================================================

    def hoverEnterEvent(self, event):
        try:
            radius = self.HOVER_RADIUS

            self.prepareGeometryChange()

            self.setRect(
                -radius,
                -radius,
                radius * 2.0,
                radius * 2.0,
            )

            self.setPen(
                QPen(
                    self.HOVER_BORDER,
                    1.5,
                )
            )

            self.setBrush(
                QBrush(
                    self.HOVER_COLOR
                )
            )

            self.update()

        except RuntimeError:
            pass

        except Exception:
            pass

        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        if not self._dragging:
            try:
                radius = self.NORMAL_RADIUS

                self.prepareGeometryChange()

                self.setRect(
                    -radius,
                    -radius,
                    radius * 2.0,
                    radius * 2.0,
                )

                self.setPen(
                    QPen(
                        self.NORMAL_BORDER,
                        1.5,
                    )
                )

                self.setBrush(
                    QBrush(
                        self.NORMAL_COLOR
                    )
                )

                self.update()

            except RuntimeError:
                pass

            except Exception:
                pass

        super().hoverLeaveEvent(event)

    # ============================================================
    # MOUSE
    # ============================================================

    def mousePressEvent(self, event):
        if (
            event.button()
            != Qt.MouseButton.LeftButton
        ):
            event.ignore()
            return

        self._dragging = True

        try:
            self.arrow.begin_bend_drag()
        except Exception:
            pass

        event.accept()

    def mouseMoveEvent(self, event):
        if not self._dragging:
            event.ignore()
            return

        try:
            scene_position = (
                self.mapToScene(
                    event.pos()
                )
            )

            self.arrow.drag_bend_to(
                scene_position
            )

        except RuntimeError:
            return

        except Exception:
            return

        event.accept()

    def mouseReleaseEvent(self, event):
        if (
            event.button()
            != Qt.MouseButton.LeftButton
        ):
            event.ignore()
            return

        self._dragging = False

        try:
            self.arrow.end_bend_drag()
        except Exception:
            pass

        event.accept()


class RoutedArrowItem(ArrowItem):
    """
    Стрелка с прямым маршрутом и одной
    контрольной точкой для ручного изгиба.

    По умолчанию стрелка прямая.

    Кружок контрольной точки виден только тогда,
    когда сама стрелка активна/выбрана.

    Геометрия начала и конца стрелки всегда
    определяется текущими точками соединения
    карточек.

    Сохранению подлежит только состояние изгиба.
    """

    ROUTED_ARROW_Z = -100.0

    BEND_HANDLE_Z = 10000.0

    def __init__(
        self,
        source_item,
        target_item=None,
        free_end=None,
    ):
        self._route_points = []

        self._router = ArrowRouter()

        self._bend_controller = (
            ArrowBendController()
        )

        self._bend_handle = None

        self._bend_handle_pending = False

        super().__init__(
            source_item=source_item,
            target_item=target_item,
            free_end=free_end,
        )

        try:
            self.setZValue(
                self.ROUTED_ARROW_Z
            )

        except RuntimeError:
            pass

        except Exception:
            pass

        self._schedule_bend_handle()

    # ============================================================
    # SELECTION
    # ============================================================

    def itemChange(
        self,
        change,
        value,
    ):
        result = super().itemChange(
            change,
            value,
        )

        try:
            if (
                change
                == self.GraphicsItemChange.ItemSelectedChange
            ):
                self._update_bend_handle_visibility(
                    bool(value)
                )

            elif (
                change
                == self.GraphicsItemChange.ItemSelectedHasChanged
            ):
                self._update_bend_handle_visibility(
                    self.isSelected()
                )

        except RuntimeError:
            pass

        except Exception:
            pass

        return result

    def _update_bend_handle_visibility(
        self,
        visible=None,
    ):
        if self._bend_handle is None:
            return

        try:
            if visible is None:
                visible = self.isSelected()

            self._bend_handle.setVisible(
                bool(visible)
            )

            if not visible:
                self._bend_handle._dragging = False

        except RuntimeError:
            pass

        except Exception:
            pass

    # ============================================================
    # BEND HANDLE
    # ============================================================

    def _schedule_bend_handle(self):
        if self._bend_handle_pending:
            return

        self._bend_handle_pending = True

        try:
            QTimer.singleShot(
                0,
                self._create_bend_handle,
            )

        except Exception:
            self._bend_handle_pending = False

    def _create_bend_handle(self):
        self._bend_handle_pending = False

        if self._being_deleted:
            return

        if self._bend_handle is not None:
            return

        try:
            scene = self.scene()

            if scene is None:
                self._schedule_bend_handle()
                return

            handle = ArrowBendHandle(
                self
            )

            handle.setZValue(
                self.BEND_HANDLE_Z
            )

            scene.addItem(
                handle
            )

            self._bend_handle = handle

            self._update_bend_handle()

            self._update_bend_handle_visibility()

        except RuntimeError:
            self._bend_handle = None

        except Exception:
            self._bend_handle = None

    def _get_local_control_point(self):
        return (
            self._bend_controller.control_point(
                self._cached_start,
                self._cached_end,
            )
        )

    def _get_scene_control_point(self):
        local_point = (
            self._get_local_control_point()
        )

        try:
            return self.mapToScene(
                local_point
            )

        except RuntimeError:
            return QPointF(
                local_point
            )

        except Exception:
            return QPointF(
                local_point
            )

    def _update_bend_handle(self):
        if self._bend_handle is None:
            return

        try:
            control_point = (
                self._get_scene_control_point()
            )

            self._bend_handle.setPos(
                control_point
            )

            self._update_bend_handle_visibility()

            self._bend_handle.update()

        except RuntimeError:
            return

        except Exception:
            return

    def begin_bend_drag(self):
        if self._being_deleted:
            return

        try:
            self.setSelected(
                True
            )

        except Exception:
            pass

        self._update_bend_handle_visibility(
            True
        )

    def drag_bend_to(
        self,
        scene_position,
    ):
        if self._being_deleted:
            return

        try:
            offset = (
                self._bend_controller.offset_from_point(
                    self._cached_start,
                    self._cached_end,
                    scene_position,
                )
            )

            self._bend_controller.offset = (
                offset
            )

            self._refresh_geometry(
                force=True
            )

            self.update()

            self._update_bend_handle()

        except RuntimeError:
            return

        except Exception:
            return

    def end_bend_drag(self):
        if self._being_deleted:
            return

        try:
            self._refresh_geometry(
                force=True
            )

            self.update()

            self._update_bend_handle()

        except RuntimeError:
            return

        except Exception:
            return

    # ============================================================
    # ROUTE
    # ============================================================

    def _calculate_route(self):
        if self._being_deleted:
            return []

        source_item = self.source_item
        target_item = self.target_item

        if source_item is None:
            return []

        try:
            if target_item is not None:
                route = self._router.route(
                    source_item,
                    target_item,
                    obstacles=None,
                )

                if route:
                    return [
                        QPointF(point)
                        for point in route
                    ]

            start_point = self._connection_point(
                source_item
            )

            if target_item is not None:
                end_point = self._connection_point(
                    target_item
                )

            else:
                end_point = QPointF(
                    self.free_end
                )

            return [
                QPointF(start_point),
                QPointF(end_point),
            ]

        except RuntimeError:
            return []

        except Exception:
            return []

    # ============================================================
    # GEOMETRY
    # ============================================================

    def _calculate_points(self):
        route = self._calculate_route()

        if route:
            self._route_points = route

            return (
                QPointF(route[0]),
                QPointF(route[-1]),
            )

        self._route_points = []

        return super()._calculate_points()

    def _make_route_bounding_rect(self):
        if not self._route_points:
            return QRectF(
                self._cached_bounding_rect
            )

        points = list(
            self._route_points
        )

        try:
            control_point = (
                self._bend_controller.control_point(
                    self._cached_start,
                    self._cached_end,
                )
            )

            points.append(
                control_point
            )

        except Exception:
            pass

        left = min(
            point.x()
            for point in points
        )

        right = max(
            point.x()
            for point in points
        )

        top = min(
            point.y()
            for point in points
        )

        bottom = max(
            point.y()
            for point in points
        )

        margin = (
            self.BOUNDING_MARGIN
            + self.ARROW_SIZE
        )

        return QRectF(
            left - margin,
            top - margin,
            max(
                right - left + margin * 2,
                margin * 2,
            ),
            max(
                bottom - top + margin * 2,
                margin * 2,
            ),
        )

    def _refresh_geometry(self, force=False):
        try:
            super()._refresh_geometry(
                force=force
            )

            if self._route_points:
                new_rect = (
                    self._make_route_bounding_rect()
                )

                if (
                    force
                    or
                    new_rect != self._cached_bounding_rect
                ):
                    self.prepareGeometryChange()

                    self._cached_bounding_rect = QRectF(
                        new_rect
                    )

            self._update_bend_handle()

        except RuntimeError:
            pass

        except Exception:
            pass

    def boundingRect(self):
        return QRectF(
            self._cached_bounding_rect
        )

    # ============================================================
    # UPDATE
    # ============================================================

    def update_position(self):
        """
        Обновляет положение стрелки после перемещения
        карточки или изменения её соединения.

        Начало и конец всегда пересчитываются
        относительно текущего положения карточек.
        """

        if self._being_deleted:
            return

        try:
            self._route_points = (
                self._calculate_route()
            )

            if self._route_points:
                self._cached_start = QPointF(
                    self._route_points[0]
                )

                self._cached_end = QPointF(
                    self._route_points[-1]
                )

                self.setLine(
                    self._cached_start.x(),
                    self._cached_start.y(),
                    self._cached_end.x(),
                    self._cached_end.y(),
                )

            if self._route_points:
                new_rect = (
                    self._make_route_bounding_rect()
                )

                self.prepareGeometryChange()

                self._cached_bounding_rect = QRectF(
                    new_rect
                )

            self._update_bend_handle()

            self.update()

            if self._bend_handle is None:
                self._schedule_bend_handle()

        except RuntimeError:
            return

        except Exception:
            return

    # ============================================================
    # CURVE
    # ============================================================

    def _build_paint_path(
        self,
        points,
    ):
        path = QPainterPath()

        if len(points) < 2:
            return path

        start_point = QPointF(
            points[0]
        )

        end_point = QPointF(
            points[-1]
        )

        if not self._bend_controller.is_bent():
            path.moveTo(
                start_point
            )

            for point in points[1:]:
                path.lineTo(
                    point
                )

            return path

        control_point = (
            self._bend_controller.control_point(
                start_point,
                end_point,
            )
        )

        path.moveTo(
            start_point
        )

        path.quadTo(
            control_point,
            end_point,
        )

        return path

    # ============================================================
    # HIT TEST
    # ============================================================

    def shape(self):
        path = QPainterPath()

        points = self._route_points

        if not points:
            points = [
                QPointF(
                    self._cached_start
                ),
                QPointF(
                    self._cached_end
                ),
            ]

        if len(points) == 1:
            path.addEllipse(
                points[0],
                self.ENDPOINT_HIT_RADIUS,
                self.ENDPOINT_HIT_RADIUS,
            )

            return path

        path = self._build_paint_path(
            points
        )

        try:
            stroker = QPainterPathStroker()

            stroker.setWidth(
                self.HIT_WIDTH
            )

            stroke = (
                stroker.createStroke(
                    path
                )
            )

            end_point = points[-1]

            endpoint_path = QPainterPath()

            endpoint_path.addEllipse(
                end_point,
                self.ENDPOINT_HIT_RADIUS,
                self.ENDPOINT_HIT_RADIUS,
            )

            stroke.addPath(
                endpoint_path
            )

            return stroke

        except Exception:
            return path

    # ============================================================
    # PAINT
    # ============================================================

    def paint(
        self,
        painter,
        option,
        widget=None,
    ):
        if self._being_deleted:
            return

        points = self._route_points

        if not points:
            points = [
                QPointF(
                    self._cached_start
                ),
                QPointF(
                    self._cached_end
                ),
            ]

        if len(points) < 2:
            return

        try:
            painter.save()

            if self.isSelected():
                color = ArrowStyle.SELECTED_COLOR
                width = ArrowStyle.SELECTED_WIDTH

            else:
                color = ArrowStyle.NORMAL_COLOR
                width = ArrowStyle.NORMAL_WIDTH

            painter.setPen(
                QPen(
                    color,
                    width,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin,
                )
            )

            painter.setBrush(
                Qt.BrushStyle.NoBrush
            )

            path = self._build_paint_path(
                points
            )

            painter.drawPath(
                path
            )

            end_point = points[-1]

            if self._bend_controller.is_bent():
                previous_point = (
                    self._bend_controller.control_point(
                        points[0],
                        end_point,
                    )
                )

            else:
                previous_point = points[-2]

            dx = (
                end_point.x()
                - previous_point.x()
            )

            dy = (
                end_point.y()
                - previous_point.y()
            )

            length_squared = (
                dx * dx
                +
                dy * dy
            )

            if length_squared > 0.0001:
                length = (
                    length_squared ** 0.5
                )

                direction_x = (
                    dx / length
                )

                direction_y = (
                    dy / length
                )

                perpendicular_x = (
                    -direction_y
                )

                perpendicular_y = (
                    direction_x
                )

                arrow_size = (
                    self.ARROW_SIZE
                )

                base = QPointF(
                    end_point.x()
                    - direction_x
                    * arrow_size,

                    end_point.y()
                    - direction_y
                    * arrow_size,
                )

                left = QPointF(
                    base.x()
                    + perpendicular_x
                    * arrow_size
                    * 0.55,

                    base.y()
                    + perpendicular_y
                    * arrow_size
                    * 0.55,
                )

                right = QPointF(
                    base.x()
                    - perpendicular_x
                    * arrow_size
                    * 0.55,

                    base.y()
                    - perpendicular_y
                    * arrow_size
                    * 0.55,
                )

                painter.setBrush(
                    QBrush(
                        color
                    )
                )

                painter.drawPolygon(
                    QPolygonF(
                        [
                            end_point,
                            left,
                            right,
                        ]
                    )
                )

            painter.restore()

        except RuntimeError:
            return

        except Exception:
            return

    # ============================================================
    # CLEANUP
    # ============================================================

    def _remove_bend_handle(self):
        handle = self._bend_handle

        if handle is None:
            return

        self._bend_handle = None

        try:
            scene = handle.scene()

            if scene is not None:
                scene.removeItem(
                    handle
                )

            del handle

        except RuntimeError:
            pass

        except Exception:
            pass

    def cleanup(self):
        """
        Удаляет только контрольную точку.

        Основная логика удаления стрелки
        остаётся в ArrowItem.
        """

        self._remove_bend_handle()

        try:
            super().cleanup()

        except RuntimeError:
            pass

        except Exception:
            pass