from PySide6.QtCore import (
    Qt,
    QRectF,
    QPointF,
)
from PySide6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QBrush,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QMenu,
)


# =========================================================
# SMART CONNECTION POINT
# =========================================================

def _smart_point(card, target_scene):
    """
    Возвращает центр ближайшей грани карточки
    в её ЛОКАЛЬНЫХ координатах, исходя из target_scene.

    Выбор грани — по вектору «центр карточки → target».
    """

    try:
        scene_rect = card.sceneBoundingRect()
        local_rect = card.boundingRect()
    except (RuntimeError, ReferenceError):
        return QPointF(0.0, 0.0)
    except Exception:
        return QPointF(0.0, 0.0)

    # Защита от пустого / нулевого rect
    try:
        if (
            scene_rect.isNull()
            or local_rect.isNull()
            or local_rect.width() <= 0
            or local_rect.height() <= 0
        ):
            return QPointF(0.0, 0.0)
    except Exception:
        return QPointF(0.0, 0.0)

    center_scene = scene_rect.center()

    dx = target_scene.x() - center_scene.x()
    dy = target_scene.y() - center_scene.y()

    if abs(dx) >= abs(dy):

        if dx >= 0:
            # правая грань
            return QPointF(
                local_rect.right(),
                local_rect.center().y(),
            )

        else:
            # левая грань
            return QPointF(
                local_rect.left(),
                local_rect.center().y(),
            )

    else:

        if dy >= 0:
            # нижняя грань
            return QPointF(
                local_rect.center().x(),
                local_rect.bottom(),
            )

        else:
            # верхняя грань
            return QPointF(
                local_rect.center().x(),
                local_rect.top(),
            )


class ArrowItem(QGraphicsItem):
    """
    Стрелка от source_item к target_item или к свободному концу.

    Точки крепления выбираются автоматически:
    центр ближайшей грани источника и цели.
    """

    ARROW_HEAD_SIZE = 10
    BOUNDING_MARGIN = 30

    MARKER_RADIUS = 6
    MARKER_HIT_RADIUS = 12

    def __init__(
        self,
        source_item,
        target_item=None,
        free_end=None,
    ):
        super().__init__()

        self.source_item = source_item
        self.target_item = target_item

        # Координаты сцены для свободного конца
        if free_end is None:
            free_end = QPointF(0.0, 0.0)

        self.free_end = QPointF(free_end)

        # Drag state
        self._dragging_end = False

        self.setZValue(-1)

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        )

        self.setAcceptedMouseButtons(
            Qt.MouseButton.LeftButton
            | Qt.MouseButton.RightButton
        )

        # Регистрируемся в карточках
        self._register_on_items()

    # =====================================================
    # ПРОВЕРКА «ЖИВОСТИ» КАРТОЧКИ
    # =====================================================

    def _is_card_alive(self, card):
        """
        Проверяет, что карточка ещё жива:
        не None, у неё есть scene() и C++ объект не удалён.
        """

        if card is None:
            return False

        try:
            if card.scene() is None:
                return False

        except (RuntimeError, ReferenceError):
            return False

        except Exception:
            return False

        return True

    # =====================================================
    # РЕГИСТРАЦИЯ В КАРТОЧКАХ
    # =====================================================

    def _register_on_items(self):
        """
        Регистрирует стрелку в source_item и target_item.
        """

        for card in (self.source_item, self.target_item):

            if not self._is_card_alive(card):
                continue

            if not hasattr(card, "arrows"):
                card.arrows = []

            if self not in card.arrows:
                card.arrows.append(self)

    def _unregister_from_items(self):
        """
        Снимает стрелку со ВСЕХ карточек, где она зарегистрирована.
        """

        for card in (self.source_item, self.target_item):

            if card is None:
                continue

            try:
                arrows = getattr(card, "arrows", None)

                if arrows is not None and self in arrows:
                    arrows.remove(self)

            except (RuntimeError, ReferenceError):
                continue

            except Exception:
                continue

    # =====================================================
    # ТОЧКИ
    # =====================================================

    def _end_scene_point(self):
        """
        Конечная точка в координатах сцены:
        либо connection_point цели, либо свободный конец.
        """

        if self._is_card_alive(self.target_item):

            try:
                local = self.target_item.connection_point()
                return self.target_item.mapToScene(local)

            except (RuntimeError, ReferenceError):
                self.target_item = None

            except Exception:
                pass

        return QPointF(self.free_end)

    def _compute_points(self):

        # Защита: источник мёртв — стрелку не рисуем.
        if not self._is_card_alive(self.source_item):
            return None

        end_scene_rough = self._end_scene_point()

        # Точка на источнике
        try:
            start_local = _smart_point(
                self.source_item,
                end_scene_rough,
            )

            start_scene = self.source_item.mapToScene(start_local)

        except (RuntimeError, ReferenceError):
            return None

        except Exception:
            return None

        # Точка на цели
        if self._is_card_alive(self.target_item):

            try:
                end_local = _smart_point(
                    self.target_item,
                    start_scene,
                )

                end_scene = self.target_item.mapToScene(end_local)

            except (RuntimeError, ReferenceError):
                self.target_item = None
                end_scene = end_scene_rough

            except Exception:
                end_scene = end_scene_rough

        else:
            end_scene = end_scene_rough

        # В локальные координаты стрелки
        try:
            start_local_arrow = self.mapFromScene(start_scene)
            end_local_arrow = self.mapFromScene(end_scene)

        except Exception:
            return None

        # Защита от NaN / inf
        for p in (start_local_arrow, end_local_arrow):

            try:
                if (
                    p.x() != p.x()
                    or p.y() != p.y()
                    or p.x() == float("inf")
                    or p.x() == float("-inf")
                    or p.y() == float("inf")
                    or p.y() == float("-inf")
                ):
                    return None

            except Exception:
                return None

        return start_local_arrow, end_local_arrow

    # =====================================================
    # ОБНОВЛЕНИЕ
    # =====================================================

    def update_position(self):
        """
        Пересчитывает boundingRect и перерисовывает.
        Вызывается карточками при перемещении.
        """

        try:
            self.prepareGeometryChange()
            self.update()

        except (RuntimeError, ReferenceError):
            pass

        except Exception:
            pass

    # =====================================================
    # ГЕОМЕТРИЯ
    # =====================================================

    def boundingRect(self):

        try:
            points = self._compute_points()

        except Exception:
            return QRectF()

        if points is None:
            return QRectF()

        start, end = points

        margin = self.BOUNDING_MARGIN

        left = min(start.x(), end.x()) - margin
        top = min(start.y(), end.y()) - margin
        right = max(start.x(), end.x()) + margin
        bottom = max(start.y(), end.y()) + margin

        # Защита от NaN / inf
        for v in (left, top, right, bottom):

            try:
                if (
                    v != v
                    or v == float("inf")
                    or v == float("-inf")
                ):
                    return QRectF()

            except Exception:
                return QRectF()

        return QRectF(
            left,
            top,
            right - left,
            bottom - top,
        )

    # =====================================================
    # PAINT
    # =====================================================

    def paint(
        self,
        painter,
        option,
        widget=None,
    ):

        try:
            points = self._compute_points()

        except Exception:
            return

        if points is None:
            return

        start_point, end_point = points

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        if self.isSelected():
            pen = QPen(
                QColor("#4F7CFF"),
                2.0,
                Qt.PenStyle.SolidLine,
            )
            marker_color = QColor("#4F7CFF")
        else:
            pen = QPen(
                QColor("#333333"),
                1.5,
                Qt.PenStyle.SolidLine,
            )
            marker_color = QColor("#FFFFFF")

        painter.setPen(pen)

        # Основная линия
        painter.drawLine(
            start_point,
            end_point,
        )

        # =================================================
        # ARROW HEAD
        # =================================================

        direction = end_point - start_point

        length = (
            direction.x() ** 2
            + direction.y() ** 2
        ) ** 0.5

        if length >= 1:

            dx = direction.x() / length
            dy = direction.y() / length

            arrow_size = self.ARROW_HEAD_SIZE

            left_point = QPointF(
                end_point.x()
                - dx * arrow_size
                + dy * arrow_size * 0.5,

                end_point.y()
                - dy * arrow_size
                - dx * arrow_size * 0.5,
            )

            right_point = QPointF(
                end_point.x()
                - dx * arrow_size
                - dy * arrow_size * 0.5,

                end_point.y()
                - dy * arrow_size
                + dx * arrow_size * 0.5,
            )

            painter.drawLine(
                end_point,
                left_point,
            )

            painter.drawLine(
                end_point,
                right_point,
            )

        # =================================================
        # МАРКЕР СВОБОДНОГО КОНЦА
        # =================================================

        painter.setBrush(
            QBrush(marker_color)
        )

        if self.isSelected():
            painter.setPen(
                QPen(
                    QColor("#4F7CFF"),
                    1.5,
                )
            )
        else:
            painter.setPen(
                QPen(
                    QColor("#777777"),
                    1.0,
                )
            )

        painter.drawEllipse(
            end_point,
            self.MARKER_RADIUS,
            self.MARKER_RADIUS,
        )

    # =====================================================
    # МЫШЬ (DRAG МАРКЕРА)
    # =====================================================

    def _is_marker_hit(self, event_pos):

        try:
            points = self._compute_points()

        except Exception:
            return False

        if points is None:
            return False

        _, end_local = points

        try:
            dx = end_local.x() - event_pos.x()
            dy = end_local.y() - event_pos.y()

        except Exception:
            return False

        return (
            dx * dx + dy * dy
            <= self.MARKER_HIT_RADIUS * self.MARKER_HIT_RADIUS
        )

    def mousePressEvent(self, event):

        if event.button() == Qt.MouseButton.LeftButton:

            if self._is_marker_hit(event.pos()):

                self._dragging_end = True
                self.setSelected(True)
                event.accept()
                return

        # ПКМ НЕ перехватываем вручную.
        # Qt сам вызовет contextMenuEvent — это безопасно.
        # Ручной вызов contextMenuEvent внутри mousePressEvent
        # приводит к access violation.

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):

        if self._dragging_end:

            scene_pos = event.scenePos()

            # Ищем карточку под курсором (не источник)
            target = self._find_target_card_at(scene_pos)

            if target is not None:

                # Если цель не изменилась — ничего не делаем
                if target is self.target_item:

                    self.update_position()
                    event.accept()
                    return

                # Снимаем стрелку СО ВСЕХ карточек,
                # где она сейчас зарегистрирована.
                # Это важно: иначе в card.arrows
                # накапливаются мёртвые ссылки,
                # и при перемещении карточек
                # приложение падает.
                self._unregister_from_items()

                # Прикрепляем к новой цели
                self.target_item = target

                # Регистрируем заново (source + target)
                self._register_on_items()

            else:

                # Открепляем — свободный конец
                if self.target_item is not None:

                    # Снимаем со всех
                    self._unregister_from_items()

                    self.target_item = None

                self.free_end = QPointF(scene_pos)

            self.update_position()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):

        if self._dragging_end:

            self._dragging_end = False

            scene = self.scene()

            if scene is not None and scene.views():

                view = scene.views()[0]
                save = getattr(view, "save_board", None)

                if save:
                    save()

            event.accept()
            return

        super().mouseReleaseEvent(event)

    def _find_target_card_at(self, scene_pos):

        scene = self.scene()

        if scene is None:
            return None

        try:
            items = scene.items(scene_pos)

        except (RuntimeError, ReferenceError):
            return None

        except Exception:
            return None

        for item in items:

            if item is self:
                continue

            if item is self.source_item:
                continue

            if not hasattr(item, "has_connection_point"):
                continue

            if not self._is_card_alive(item):
                continue

            try:
                if not item.has_connection_point():
                    continue

                local = item.mapFromScene(scene_pos)
                rect = item.boundingRect()

                if rect.contains(local):
                    return item

            except (RuntimeError, ReferenceError):
                continue

            except Exception:
                continue

        return None

    # =====================================================
    # CONTEXT MENU
    # =====================================================

    def contextMenuEvent(self, event):
        """
        Вызывается Qt автоматически по ПКМ.

        Не вызывать этот метод вручную из mousePressEvent —
        это приводит к access violation.
        """

        menu = QMenu()

        delete_action = menu.addAction(
            "Удалить стрелку"
        )

        action = menu.exec(
            event.screenPos()
        )

        if action == delete_action:

            self._unregister_from_items()

            scene = self.scene()

            if scene is not None:

                try:
                    scene.removeItem(self)

                except (RuntimeError, ReferenceError):
                    pass

                except Exception:
                    pass

                views = scene.views()

                if views:

                    save = getattr(
                        views[0],
                        "save_board",
                        None,
                    )

                    if save:
                        save()