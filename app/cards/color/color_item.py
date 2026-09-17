import uuid

from PySide6.QtCore import Qt, QRectF, QPoint
from PySide6.QtGui import QColor, QPen, QBrush, QPainter, QFont
from PySide6.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsItem,
    QMenu,
    QApplication,
)


class ColorItem(QGraphicsRectItem):

    MIN_WIDTH = 260
    MIN_HEIGHT = 220

    RESIZE_HANDLE_SIZE = 24

    CONNECTION_POINT_RADIUS = 3.5
    CONNECTION_POINT_DISTANCE = 8

    SIDE_MARGIN = 14
    TOP_MARGIN = 14
    BOTTOM_MARGIN = 14
    CODE_HEIGHT = 42
    GAP = 10

    def __init__(
        self,
        color="#FFFFFF",
        width=280,
        height=240,
    ):
        super().__init__(
            0,
            0,
            max(self.MIN_WIDTH, width),
            max(self.MIN_HEIGHT, height),
        )

        self.card_id = str(uuid.uuid4())
        self.card_type = "color"

        valid_color = QColor(color)

        if not valid_color.isValid():
            valid_color = QColor("#FFFFFF")

        self.card_color = valid_color.name()

        self.connection_hovered = False

        self.resizing = False
        self.resize_start = None
        self.original_width = self.rect().width()
        self.original_height = self.rect().height()

        # Привязка к рамке (устанавливается frame_containment)
        self._frame = None

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        )

        self.setAcceptHoverEvents(True)

        self.arrows = []

    def set_color(self, color):
        valid_color = QColor(color)

        if not valid_color.isValid():
            return

        self.card_color = valid_color.name()
        self.update()

        self.save_board()

    def has_connection_point(self):
        return True

    def connection_point(self):
        rect = self.rect()

        return rect.bottomRight()

    def resize_zone(self, pos):
        rect = self.rect()

        return (
            pos.x() >= rect.width() - self.RESIZE_HANDLE_SIZE
            and
            pos.y() >= rect.height() - self.RESIZE_HANDLE_SIZE
        )

    def itemChange(
        self,
        change,
        value,
    ):

        if (
            change
            == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged
        ):

            arrows = getattr(self, "arrows", None)

            if arrows:

                for arrow in list(arrows):

                    try:
                        arrow.update_position()

                    except Exception:
                        pass

        return super().itemChange(
            change,
            value,
        )

    def save_board(self):
        if not self.scene():
            return

        views = self.scene().views()

        if not views:
            return

        view = views[0]

        save_method = getattr(view, "save_board", None)

        if save_method:
            save_method()

    def hoverMoveEvent(self, event):

        if self.resize_zone(event.pos()):
            self.setCursor(
                Qt.CursorShape.SizeFDiagCursor
            )
        else:
            self.setCursor(
                Qt.CursorShape.ArrowCursor
            )

        point = self.connection_point()

        distance = event.pos() - point

        self.connection_hovered = (
            distance.x() ** 2
            +
            distance.y() ** 2
            <=
            (
                self.CONNECTION_POINT_RADIUS
                +
                self.CONNECTION_POINT_DISTANCE
            ) ** 2
        )

        self.update()

        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):

        self.connection_hovered = False

        self.setCursor(
            Qt.CursorShape.ArrowCursor
        )

        self.update()

        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):

        if (
            event.button() == Qt.MouseButton.LeftButton
            and
            self.resize_zone(event.pos())
        ):

            self.resizing = True
            self.resize_start = event.pos()

            self.original_width = self.rect().width()
            self.original_height = self.rect().height()

            self.setSelected(True)

            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):

        if self.resizing:

            delta = event.pos() - self.resize_start

            new_width = max(
                self.MIN_WIDTH,
                self.original_width + delta.x(),
            )

            new_height = max(
                self.MIN_HEIGHT,
                self.original_height + delta.y(),
            )

            self.prepareGeometryChange()

            self.setRect(
                0,
                0,
                new_width,
                new_height,
            )

            self.update()

            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):

        if (
            event.button() == Qt.MouseButton.LeftButton
            and
            self.resizing
        ):

            self.resizing = False
            self.resize_start = None

            self.unsetCursor()

            self.save_board()

            event.accept()
            return

        super().mouseReleaseEvent(event)

        # =====================================================
        # FRAME MEMBERSHIP
        # =====================================================

        if event.button() == Qt.MouseButton.LeftButton:

            try:
                from ...canvas.frame_containment import (
                    update_item_membership,
                )

                update_item_membership(
                    self,
                    self.scene(),
                )

                self.save_board()

            except Exception as exc:
                print(
                    f"[COLOR] membership update failed: {exc!r}"
                )

    def contextMenuEvent(self, event):

        menu = QMenu()

        change_color_action = menu.addAction(
            "Изменить цвет"
        )

        menu.addSeparator()

        delete_action = menu.addAction(
            "Удалить"
        )

        action = menu.exec(
            event.screenPos()
        )

        if action == change_color_action:

            self._open_color_ring()

        elif action == delete_action:

            if self.scene() and self.scene().views():

                view = self.scene().views()[0]

                delete_method = getattr(
                    view,
                    "delete_item",
                    None,
                )

                if delete_method:
                    delete_method(self)

        event.accept()

    def _open_color_ring(self):

        view = None

        if self.scene() and self.scene().views():
            view = self.scene().views()[0]

        from ...canvas.color_ring import ColorRingPopup

        popup = ColorRingPopup(
            view,
            initial_color=self.card_color,
        )

        if view is not None:

            scene_rect = self.sceneBoundingRect()

            top_right_scene = scene_rect.topRight()

            top_right_view = view.mapFromScene(
                top_right_scene
            )

            global_pos = view.viewport().mapToGlobal(
                QPoint(
                    top_right_view.x() + 10,
                    top_right_view.y(),
                )
            )

        else:

            from PySide6.QtGui import QCursor
            global_pos = QCursor.pos()

        popup.show_at(global_pos)

        while popup.isVisible():
            QApplication.processEvents()

        color = popup.get_color()

        if color.isValid():

            self.card_color = color.name()
            self.update()

            self.save_board()

            if view is not None:

                main_window = getattr(
                    view,
                    "main_window",
                    None,
                )

                if main_window is not None:
                    main_window.update_status(
                        "Цвет изменен"
                    )

    def paint(self, painter, option, widget=None):

        painter.save()

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        rect = self.rect()

        painter.setClipRect(rect)

        shadow_rect = rect.adjusted(
            3,
            4,
            3,
            5,
        )

        painter.setPen(
            Qt.PenStyle.NoPen
        )

        painter.setBrush(
            QColor(
                0,
                0,
                0,
                18,
            )
        )

        painter.drawRect(shadow_rect)

        painter.setBrush(
            QColor(
                250,
                250,
                247,
            )
        )

        if self.isSelected():

            painter.setPen(
                QPen(
                    QColor("#4F7CFF"),
                    2,
                )
            )

        else:

            painter.setPen(
                QPen(
                    QColor(
                        215,
                        215,
                        210,
                    ),
                    1,
                )
            )

        painter.drawRect(rect)

        inner_left = float(self.SIDE_MARGIN)
        inner_right = float(self.SIDE_MARGIN)
        inner_top = float(self.TOP_MARGIN)
        inner_bottom = float(self.BOTTOM_MARGIN)

        card_width = float(rect.width())
        card_height = float(rect.height())

        inner_width = max(
            1.0,
            card_width
            - inner_left
            - inner_right,
        )

        inner_height = max(
            1.0,
            card_height
            - inner_top
            - inner_bottom,
        )

        code_height = min(
            float(self.CODE_HEIGHT),
            inner_height,
        )

        code_top = (
            card_height
            - inner_bottom
            - code_height
        )

        code_top = max(
            inner_top,
            code_top,
        )

        color_top = inner_top

        color_bottom = code_top - self.GAP

        color_height = max(
            1.0,
            color_bottom - color_top,
        )

        color_rect = QRectF(
            inner_left,
            color_top,
            inner_width,
            color_height,
        )

        painter.setBrush(
            QColor(self.card_color)
        )

        painter.setPen(
            QPen(
                QColor(
                    205,
                    205,
                    200,
                ),
                1,
            )
        )

        painter.drawRect(color_rect)

        code_rect = QRectF(
            inner_left,
            code_top,
            inner_width,
            code_height,
        )

        code_rect = code_rect.intersected(rect)

        painter.setBrush(
            QColor(
                242,
                242,
                238,
            )
        )

        painter.setPen(
            QPen(
                QColor(
                    220,
                    220,
                    215,
                ),
                1,
            )
        )

        painter.drawRect(code_rect)

        color = QColor(self.card_color)

        if not color.isValid():
            color = QColor("#FFFFFF")

        code = color.name().upper()

        painter.setPen(
            QColor(
                68,
                68,
                68,
            )
        )

        code_font = QFont(
            "Segoe UI",
            11,
        )

        code_font.setBold(True)

        painter.setFont(code_font)

        painter.drawText(
            code_rect,
            Qt.AlignmentFlag.AlignCenter,
            code,
        )

        point = self.connection_point()

        if self.connection_hovered:

            radius = (
                self.CONNECTION_POINT_RADIUS
                + 1.5
            )

            painter.setBrush(
                QColor("#FFFFFF")
            )

            painter.setPen(
                QPen(
                    QColor("#202124"),
                    1.5,
                )
            )

        else:

            radius = self.CONNECTION_POINT_RADIUS

            painter.setBrush(
                QColor("#FFFFFF")
            )

            painter.setPen(
                QPen(
                    QColor("#8A8A86"),
                    1,
                )
            )

        painter.drawEllipse(
            point,
            radius,
            radius,
        )

        painter.restore()