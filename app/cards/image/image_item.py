import uuid

from PySide6.QtCore import (
    Qt,
    QPointF,
)
from PySide6.QtGui import (
    QColor,
    QBrush,
    QPen,
)
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsItem,
    QMenu,
)


class ImageItem(QGraphicsPixmapItem):

    RESIZE_HANDLE_SIZE = 24

    MIN_WIDTH = 80
    MIN_HEIGHT = 80

    CONNECTION_POINT_RADIUS = 5

    def __init__(
        self,
        pixmap,
        image_path="",
    ):
        super().__init__(
            pixmap
        )

        self.image_path = image_path

        self.image_id = str(
            uuid.uuid4()
        )

        self.original_pixmap = pixmap

        self.card_color = QColor(
            0,
            0,
            0,
            0,
        )

        # Привязка к рамке (устанавливается frame_containment)
        self._frame = None

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        )

        self.setShapeMode(
            QGraphicsPixmapItem.ShapeMode.BoundingRectShape
        )

        self.setTransformationMode(
            Qt.TransformationMode.SmoothTransformation
        )

        self.resizing = False
        self.resize_start = None

        self.original_width = pixmap.width()
        self.original_height = pixmap.height()

        self.saved_scale = 1.0

        self.arrows = []

    def set_card_color(
        self,
        color,
    ):
        if isinstance(
            color,
            str,
        ):
            color = QColor(
                color
            )

        if not isinstance(
            color,
            QColor,
        ):
            return

        self.card_color = QColor(
            color
        )

        self.update()

    def get_card_color(
        self,
    ):
        return QColor(
            self.card_color
        )

    def card_color_name(
        self,
    ):
        return self.card_color.name(
            QColor.NameFormat.HexArgb
        )

    def has_connection_point(
        self,
    ):
        return True

    def connection_point(
        self,
    ):
        rect = self.boundingRect()

        radius = self.CONNECTION_POINT_RADIUS

        return QPointF(
            rect.right() - radius,
            rect.bottom() - radius,
        )

    def resize_zone(
        self,
        pos,
    ):
        rect = self.boundingRect()

        return (
            pos.x()
            >=
            rect.right()
            -
            self.RESIZE_HANDLE_SIZE
            and
            pos.y()
            >=
            rect.bottom()
            -
            self.RESIZE_HANDLE_SIZE
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

    def hoverMoveEvent(
        self,
        event,
    ):
        if self.resize_zone(
            event.pos()
        ):
            self.setCursor(
                Qt.CursorShape.SizeFDiagCursor
            )
        else:
            self.setCursor(
                Qt.CursorShape.ArrowCursor
            )

        super().hoverMoveEvent(
            event
        )

    def mousePressEvent(
        self,
        event,
    ):
        if (
            event.button()
            ==
            Qt.MouseButton.LeftButton
            and
            self.resize_zone(
                event.pos()
            )
        ):
            self.resizing = True

            self.resize_start = (
                event.scenePos()
            )

            self.original_width = (
                self.pixmap().width()
            )

            self.original_height = (
                self.pixmap().height()
            )

            event.accept()

            return

        super().mousePressEvent(
            event
        )

    def mouseMoveEvent(
        self,
        event,
    ):
        if self.resizing:

            delta = (
                event.scenePos()
                -
                self.resize_start
            )

            new_width = max(
                self.MIN_WIDTH,
                self.original_width
                +
                delta.x(),
            )

            if self.original_pixmap.width() == 0:
                event.accept()
                return

            aspect_ratio = (
                self.original_pixmap.height()
                /
                self.original_pixmap.width()
            )

            new_height = (
                new_width
                *
                aspect_ratio
            )

            new_height = max(
                self.MIN_HEIGHT,
                new_height,
            )

            scaled = (
                self.original_pixmap.scaled(
                    int(new_width),
                    int(new_height),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

            self.setPixmap(
                scaled
            )

            self.saved_scale = (
                new_width
                /
                self.original_width
            )

            self.update()

            event.accept()

            return

        super().mouseMoveEvent(
            event
        )

    def mouseReleaseEvent(
        self,
        event,
    ):
        if (
            event.button()
            ==
            Qt.MouseButton.LeftButton
            and
            self.resizing
        ):
            self.resizing = False

            self.resize_start = None

            self.unsetCursor()

            self._save_board()

            event.accept()

            return

        super().mouseReleaseEvent(
            event
        )

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

                self._save_board()

            except Exception as exc:
                print(
                    f"[IMAGE] membership update failed: {exc!r}"
                )

    def _save_board(
        self,
    ):
        if not self.scene():
            return

        views = (
            self.scene().views()
        )

        if not views:
            return

        view = views[0]

        if hasattr(
            view,
            "save_board",
        ):
            view.save_board()

    def contextMenuEvent(
        self,
        event,
    ):
        menu = QMenu()

        color_action = menu.addAction(
            "Цвет карточки..."
        )

        reset_color_action = menu.addAction(
            "Сбросить цвет"
        )

        menu.addSeparator()

        delete_action = menu.addAction(
            "Удалить"
        )

        action = menu.exec(
            event.screenPos()
        )

        if action == color_action:

            from ...canvas.color import show_palette

            color = show_palette(
                None,
                self.card_color,
            )

            if color.isValid():

                self.set_card_color(
                    color
                )

                self._save_board()

        elif action == reset_color_action:

            self.set_card_color(
                QColor(
                    0,
                    0,
                    0,
                    0,
                )
            )

            self._save_board()

        elif action == delete_action:

            if self.scene():

                views = (
                    self.scene().views()
                )

                if views:

                    view = views[0]

                    if hasattr(
                        view,
                        "main_window",
                    ) and view.main_window:

                        view.delete_item(
                            self
                        )

        event.accept()

    def paint(
        self,
        painter,
        option,
        widget=None,
    ):
        painter.setRenderHint(
            painter.RenderHint.Antialiasing,
            True,
        )

        if self.card_color.alpha() > 0:

            painter.setPen(
                Qt.PenStyle.NoPen
            )

            painter.setBrush(
                QBrush(
                    self.card_color
                )
            )

            painter.drawRect(
                self.boundingRect()
            )

        super().paint(
            painter,
            option,
            widget,
        )

        point = (
            self.connection_point()
        )

        radius = (
            self.CONNECTION_POINT_RADIUS
        )

        painter.setPen(
            QPen(
                QColor("#777777"),
                1,
            )
        )

        painter.setBrush(
            QBrush(
                QColor("#FFFFFF")
            )
        )

        painter.drawEllipse(
            point,
            radius,
            radius,
        )