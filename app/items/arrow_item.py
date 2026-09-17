import math
import shiboken6

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QPen,
    QBrush,
    QColor,
    QPainterPath,
    QPolygonF,
)
from PySide6.QtWidgets import QGraphicsLineItem, QMenu


class ArrowItem(QGraphicsLineItem):

    BOUNDING_MARGIN = 20.0
    ARROW_SIZE = 7.0

    # Реальная визуальная линия 2 px,
    # но зона захвата будет значительно шире.
    HIT_WIDTH = 14.0

    # Дополнительная зона захвата кончика.
    ENDPOINT_HIT_RADIUS = 18.0

    def __init__(
        self,
        source_item,
        target_item=None,
        free_end=None,
    ):
        super().__init__()

        self.source_item = source_item
        self.target_item = target_item

        self.free_end = (
            QPointF(free_end)
            if free_end is not None
            else QPointF(0.0, 0.0)
        )

        self.card_id = None

        # Индекс точки подключения источника (0-3) или None.
        self.source_point_index = None
        self._being_deleted = False

        self._cached_start = QPointF(0.0, 0.0)
        self._cached_end = QPointF(0.0, 0.0)

        self._cached_bounding_rect = QRectF(
            -self.BOUNDING_MARGIN,
            -self.BOUNDING_MARGIN,
            self.BOUNDING_MARGIN * 2,
            self.BOUNDING_MARGIN * 2,
        )

        self._geometry_initialized = False

        self.setZValue(1000)

        self.setFlag(
            QGraphicsLineItem.GraphicsItemFlag.ItemIsSelectable,
            True,
        )

        self.setAcceptedMouseButtons(
            Qt.MouseButton.LeftButton
            | Qt.MouseButton.RightButton
        )

        self.setPen(
            QPen(
                QColor("#7A7A7A"),
                1.5,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )

        self._register_on_items()

        self._refresh_geometry(force=True)

        self._debug(
            "CREATE ArrowItem "
            f"id={id(self)} "
            f"source={self._item_name(self.source_item)} "
            f"target={self._item_name(self.target_item)} "
            f"free_end=({self.free_end.x():.2f}, {self.free_end.y():.2f})"
        )

    # ============================================================
    # DEBUG
    # ============================================================

    def _debug(self, message):
        try:
            with open(
                "devjournal_arrow_debug.log",
                "a",
                encoding="utf-8",
            ) as file:
                from datetime import datetime

                timestamp = datetime.now().strftime(
                    "%H:%M:%S.%f"
                )[:-3]

                file.write(
                    f"[{timestamp}] {message}\n"
                )
        except Exception:
            pass

    @staticmethod
    def _item_name(item):
        if item is None:
            return "None"

        try:
            return type(item).__name__
        except Exception:
            return "Unknown"

    @staticmethod
    def _is_card_alive(item):
        if item is None:
            return False

        try:
            return shiboken6.isValid(item)
        except Exception:
            return False

    # ============================================================
    # REGISTRATION
    # ============================================================

    def _register_on_item(self, item):
        if not self._is_card_alive(item):
            return

        try:
            arrows = getattr(item, "arrows", None)

            if arrows is None:
                arrows = []
                item.arrows = arrows

            if self not in arrows:
                arrows.append(self)

                self._debug(
                    "REGISTERED "
                    f"arrow={id(self)} "
                    f"card={self._item_name(item)} "
                    f"count={len(arrows)}"
                )

        except Exception as exc:
            self._debug(
                "REGISTER ERROR "
                f"arrow={id(self)} "
                f"card={self._item_name(item)} "
                f"error={exc!r}"
            )

    def _unregister_from_item(self, item):
        if not self._is_card_alive(item):
            return

        try:
            arrows = getattr(item, "arrows", None)

            if not arrows:
                return

            while self in arrows:
                arrows.remove(self)

            self._debug(
                "UNREGISTERED "
                f"arrow={id(self)} "
                f"card={self._item_name(item)} "
                f"count={len(arrows)}"
            )

        except Exception as exc:
            self._debug(
                "UNREGISTER ERROR "
                f"arrow={id(self)} "
                f"card={self._item_name(item)} "
                f"error={exc!r}"
            )

    def _register_on_items(self):
        self._register_on_item(self.source_item)
        self._register_on_item(self.target_item)

    def _unregister_from_items(self):
        self._unregister_from_item(self.source_item)
        self._unregister_from_item(self.target_item)

    # ============================================================
    # TARGET
    # ============================================================

    def _set_target(self, target):
        if target is self.target_item:
            return

        old_target = self.target_item

        if old_target is not None:
            self._unregister_from_item(old_target)

        self.target_item = target

        if target is not None:
            self._register_on_item(target)

        self._debug(
            "TARGET CHANGED "
            f"arrow={id(self)} "
            f"old={self._item_name(old_target)} "
            f"new={self._item_name(target)}"
        )

    # ============================================================
    # CONNECTION POINTS
    # ============================================================

    def _get_other_end_scene_point(self, item):
        """
        Возвращает координаты противоположного конца стрелки
        в координатах сцены.

        Если item == source_item, "другой конец" — target_item
        или free_end.
        Если item == target_item, "другой конец" — source_item.
        """

        try:
            if item is self.source_item:
                target = self.target_item

                if self._is_card_alive(target):
                    return self._connection_point(target)

                return QPointF(self.free_end)

            if item is self.target_item:
                source = self.source_item

                if self._is_card_alive(source):
                    return self._connection_point(source)
        except Exception:
            pass

        return None

    def _nearest_point_index(self, item, other_scene_point):
        """
        Возвращает индекс ближайшей точки подключения item
        к other_scene_point (в координатах сцены).
        """

        try:
            from ..cards.base.connection import connection_points
        except Exception:
            return None

        if other_scene_point is None:
            return None

        try:
            points = connection_points(item)
        except Exception:
            return None

        if not points:
            return None

        try:
            local_other = item.mapFromScene(other_scene_point)
        except Exception:
            return None

        best_index = 0
        best_distance = None

        for i, p in enumerate(points):
            dx = p.x() - local_other.x()
            dy = p.y() - local_other.y()
            dist = dx * dx + dy * dy

            if best_distance is None or dist < best_distance:
                best_distance = dist
                best_index = i

        return best_index

    def _connection_point(self, item):
        if not self._is_card_alive(item):
            return QPointF(0.0, 0.0)

        try:
            method = getattr(
                item,
                "connection_point",
                None,
            )

            if callable(method):

                point_index = None

                # Для ИСТОЧНИКА — динамически выбираем ближайшую
                # точку к противоположному концу стрелки.
                # Для цели и всего остального — старая логика.
                try:
                    if item is self.source_item:
                        other = self._get_other_end_scene_point(item)

                        if other is not None:
                            point_index = self._nearest_point_index(
                                item,
                                other,
                            )
                except Exception:
                    point_index = None

                # Fallback — на случай, если динамика не сработала:
                # берём сохранённый source_point_index.
                if point_index is None:
                    try:
                        if item is self.source_item:
                            point_index = getattr(
                                self,
                                "source_point_index",
                                None,
                            )
                    except Exception:
                        point_index = None

                try:
                    local_point = method(point_index)
                except TypeError:
                    local_point = method()

                return item.mapToScene(local_point)

        except Exception as exc:
            self._debug(
                "CONNECTION POINT ERROR "
                f"arrow={id(self)} "
                f"item={self._item_name(item)} "
                f"error={exc!r}"
            )

        try:
            return item.sceneBoundingRect().center()
        except Exception:
            return QPointF(0.0, 0.0)

    def _get_end_scene_point(self):
        target = self.target_item

        if self._is_card_alive(target):
            try:
                return self._connection_point(target)
            except Exception:
                pass

        return QPointF(self.free_end)

    # ============================================================
    # GEOMETRY
    # ============================================================

    def _calculate_points(self):
        start_scene = self._connection_point(
            self.source_item
        )

        end_scene = self._get_end_scene_point()

        return (
            QPointF(start_scene),
            QPointF(end_scene),
        )

    def _make_bounding_rect(
        self,
        start_point,
        end_point,
    ):
        left = min(
            start_point.x(),
            end_point.x(),
        )

        right = max(
            start_point.x(),
            end_point.x(),
        )

        top = min(
            start_point.y(),
            end_point.y(),
        )

        bottom = max(
            start_point.y(),
            end_point.y(),
        )

        margin = self.BOUNDING_MARGIN

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
            start_point, end_point = self._calculate_points()

            new_rect = self._make_bounding_rect(
                start_point,
                end_point,
            )

            geometry_changed = (
                force
                or not self._geometry_initialized
                or start_point != self._cached_start
                or end_point != self._cached_end
                or new_rect != self._cached_bounding_rect
            )

            if not geometry_changed:
                return

            if self._geometry_initialized:
                self.prepareGeometryChange()

            self._cached_start = QPointF(start_point)
            self._cached_end = QPointF(end_point)
            self._cached_bounding_rect = QRectF(new_rect)

            self.setLine(
                self._cached_start.x(),
                self._cached_start.y(),
                self._cached_end.x(),
                self._cached_end.y(),
            )

            self._geometry_initialized = True

        except RuntimeError as exc:
            self._debug(
                "GEOMETRY RUNTIME ERROR "
                f"arrow={id(self)} "
                f"error={exc!r}"
            )

        except Exception as exc:
            self._debug(
                "GEOMETRY ERROR "
                f"arrow={id(self)} "
                f"error={exc!r}"
            )

    def update_position(self):
        if self._being_deleted:
            return

        if not self._geometry_initialized:
            self._refresh_geometry(force=True)
        else:
            self._refresh_geometry()

        try:
            self.update()
        except RuntimeError:
            pass
        except Exception:
            pass

    # ============================================================
    # QT GEOMETRY
    # ============================================================

    def boundingRect(self):
        return QRectF(self._cached_bounding_rect)

    # ============================================================
    # HIT TEST
    # ============================================================

    def shape(self):
        """
        Увеличенная невидимая область захвата стрелки.

        Визуально стрелка остаётся 2 px,
        но клик по линии допускается с заметным запасом.
        """

        path = QPainterPath()

        start = self._cached_start
        end = self._cached_end

        try:
            hit_pen = QPen()
            hit_pen.setWidthF(self.HIT_WIDTH)

            path.moveTo(start)
            path.lineTo(end)

            stroke = QPainterPath()

            # Создаём контур вокруг линии.
            stroker = QPainterPath()
            stroker.addPath(path)

            # РСЃРїРѕР»СЊР·СѓРµРј QPainterPathStroker С‡РµСЂРµР· QtGui.
            from PySide6.QtGui import QPainterPathStroker

            path_stroker = QPainterPathStroker()
            path_stroker.setWidth(self.HIT_WIDTH)

            stroke = path_stroker.createStroke(path)

            # Отдельно расширяем область возле кончика.
            radius = self.ENDPOINT_HIT_RADIUS

            endpoint_path = QPainterPath()
            endpoint_path.addEllipse(
                end,
                radius,
                radius,
            )

            stroke.addPath(endpoint_path)

            return stroke

        except Exception:
            # Безопасный fallback.
            path.addEllipse(
                end,
                self.ENDPOINT_HIT_RADIUS,
                self.ENDPOINT_HIT_RADIUS,
            )

            path.moveTo(start)
            path.lineTo(end)

            return path

    def _is_marker_hit(self, scene_pos):
        try:
            dx = (
                scene_pos.x()
                - self._cached_end.x()
            )

            dy = (
                scene_pos.y()
                - self._cached_end.y()
            )

            return (
                dx * dx
                +
                dy * dy
                <=
                self.ENDPOINT_HIT_RADIUS
                *
                self.ENDPOINT_HIT_RADIUS
            )

        except Exception:
            return False

    # ============================================================
    # MOUSE
    # ============================================================

    def mousePressEvent(self, event):
        if self._being_deleted:
            event.ignore()
            return

        if event.button() == Qt.MouseButton.RightButton:
            self.contextMenuEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self._debug(
                "DRAG START "
                f"arrow={id(self)}"
            )

            self.setSelected(True)

            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._being_deleted:
            event.ignore()
            return

        if not (
            event.buttons()
            & Qt.MouseButton.LeftButton
        ):
            super().mouseMoveEvent(event)
            return

        try:
            scene_pos = event.scenePos()

            target = None

            scene = self.scene()

            if scene is not None:
                items = scene.items(
                    scene_pos
                )

                for item in items:
                    if item is self:
                        continue

                    if item is self.source_item:
                        continue

                    if not self._is_card_alive(item):
                        continue

                    has_connection = getattr(
                        item,
                        "has_connection_point",
                        None,
                    )

                    if callable(has_connection):
                        try:
                            if has_connection():
                                target = item
                                break
                        except Exception:
                            continue

            if target is not None:
                self._set_target(target)
            else:
                if self.target_item is not None:
                    self._set_target(None)

                self.free_end = QPointF(scene_pos)

            self.update_position()

            event.accept()

        except Exception as exc:
            self._debug(
                "DRAG ERROR "
                f"arrow={id(self)} "
                f"error={exc!r}"
            )

            event.accept()

    def mouseReleaseEvent(self, event):
        if self._being_deleted:
            event.ignore()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self._debug(
                "DRAG END "
                f"arrow={id(self)}"
            )

            self.update_position()

            event.accept()
            return

        super().mouseReleaseEvent(event)

    # ============================================================
    # CONTEXT MENU
    # ============================================================

    def contextMenuEvent(self, event):
        if self._being_deleted:
            event.accept()
            return

        self._debug(
            "CONTEXT MENU "
            f"arrow={id(self)}"
        )

        menu = QMenu()

        delete_action = menu.addAction(
            "Удалить стрелку"
        )

        action = menu.exec(
            event.screenPos()
        )

        if action == delete_action:
            self.delete_arrow()

        event.accept()

    # ============================================================
    # DELETE
    # ============================================================

    def delete_arrow(self):
        if self._being_deleted:
            return

        self._debug(
            "DELETE START "
            f"arrow={id(self)}"
        )

        # Вызываем cleanup() ДО установки _being_deleted.
        # Иначе cleanup сразу выйдет из-за проверки.
        try:
            cleanup = getattr(self, "cleanup", None)

            if callable(cleanup):
                cleanup()
        except Exception:
            pass

        self._being_deleted = True

        try:
            view = None
            scene = self.scene()

            if scene is not None:
                views = scene.views()

                if views:
                    view = views[0]

            self._unregister_from_items()

            self.source_item = None
            self.target_item = None

            if scene is not None:
                try:
                    scene.removeItem(self)

                    self._debug(
                        "SCENE REMOVE "
                        f"arrow={id(self)}"
                    )

                except RuntimeError as exc:
                    self._debug(
                        "SCENE REMOVE RUNTIME ERROR "
                        f"arrow={id(self)} "
                        f"error={exc!r}"
                    )

                except Exception as exc:
                    self._debug(
                        "SCENE REMOVE ERROR "
                        f"arrow={id(self)} "
                        f"error={exc!r}"
                    )

            self._debug(
                "DELETE END "
                f"arrow={id(self)}"
            )

            if view is not None:
                try:
                    save_method = getattr(
                        view,
                        "save_board",
                        None,
                    )

                    if callable(save_method):
                        save_method()

                except Exception as exc:
                    self._debug(
                        "SAVE AFTER DELETE ERROR "
                        f"arrow={id(self)} "
                        f"error={exc!r}"
                    )

        except Exception as exc:
            self._debug(
                "DELETE ERROR "
                f"arrow={id(self)} "
                f"error={exc!r}"
            )

    # ============================================================
    # CLEANUP
    # ============================================================

    def cleanup(self):
        pass

    def _cleanup_impl(self):
        if self._being_deleted:
            return

        self._being_deleted = True

        self._debug(
            "CLEANUP START "
            f"arrow={id(self)}"
        )

        try:
            self._unregister_from_items()
        except Exception:
            pass

        self.source_item = None
        self.target_item = None

        self._debug(
            "CLEANUP END "
            f"arrow={id(self)}"
        )

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

        try:
            start = self._cached_start
            end = self._cached_end

            dx = end.x() - start.x()
            dy = end.y() - start.y()

            length = math.hypot(
                dx,
                dy,
            )

            if length < 0.001:
                return

            angle_x = dx / length
            angle_y = dy / length

            perp_x = -angle_y
            perp_y = angle_x

            arrow_size = self.ARROW_SIZE

            base = QPointF(
                end.x() - angle_x * arrow_size,
                end.y() - angle_y * arrow_size,
            )

            left = QPointF(
                base.x()
                + perp_x * arrow_size * 0.55,
                base.y()
                + perp_y * arrow_size * 0.55,
            )

            right = QPointF(
                base.x()
                - perp_x * arrow_size * 0.55,
                base.y()
                - perp_y * arrow_size * 0.55,
            )

            painter.save()

            if self.isSelected():
                painter.setPen(
                    QPen(
                        QColor("#4F7CFF"),
                2.0,
                        Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap,
                        Qt.PenJoinStyle.RoundJoin,
                    )
                )
            else:
                painter.setPen(
                    QPen(
                        QColor("#7A7A7A"),
                1.5,
                        Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap,
                        Qt.PenJoinStyle.RoundJoin,
                    )
                )

            painter.setBrush(
                QBrush(
                    painter.pen().color()
                )
            )

            painter.drawLine(
                start,
                end,
            )

            painter.drawPolygon(
                QPolygonF(
                    [
                        end,
                        left,
                        right,
                    ]
                )
            )

            painter.restore()

        except RuntimeError as exc:
            self._debug(
                "PAINT RUNTIME ERROR "
                f"arrow={id(self)} "
                f"error={exc!r}"
            )

        except Exception as exc:
            self._debug(
                "PAINT ERROR "
                f"arrow={id(self)} "
                f"error={exc!r}"
            )

    # ============================================================
    # DESTRUCTOR
    # ============================================================

    def __del__(self):
        try:
            self._debug(
                "DESTRUCTOR "
                f"arrow={id(self)}"
            )
        except Exception:
            pass