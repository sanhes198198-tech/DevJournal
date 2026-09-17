from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QColor,
    QBrush,
    QPen,
    QPainter,
    QPixmap,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QFileDialog,
    QMenu,
)

import os
import uuid
import shutil

from ...utils import ensure_project_folder

from .editable_text import EditableText

from .connection import (
    has_connection_point,
    connection_point,
    update_connection_hover,
    paint_connection_point,
)

from .resize import (
    resize_zone,
    start_resize,
    calculate_resize,
    finish_resize,
)


class Card(QGraphicsRectItem):

    MIN_TEXT_WIDTH = 220
    MIN_TEXT_HEIGHT = 140

    MIN_COMMENT_WIDTH = 250
    MIN_COMMENT_HEIGHT = 70

    MIN_HEADING_WIDTH = 320
    MIN_HEADING_HEIGHT = 150

    MIN_IMAGE_WIDTH = 320
    MIN_IMAGE_HEIGHT = 390

    MIN_COLOR_WIDTH = 260
    MIN_COLOR_HEIGHT = 220

    def __init__(
        self,
        x=0,
        y=0,
        width=220,
        height=140,
        card_type="text",
        title="",
        body="",
        color="#FFFFFF",
    ):
        super().__init__(
            QRectF(
                0,
                0,
                width,
                height,
            )
        )

        self.card_type = card_type
        self.title_text = title
        self.body_text = body

        self.card_color = self._normalize_color(
            color
        )

        self.card_id = None

        self.connection_hovered = False
        self.hover_point_index = None

        self.resizing = False
        self.resize_start_pos = None
        self.resize_start_size = None

        # image-specific
        self.image_pixmap = QPixmap()
        self.image_path = ""
        self.image_aspect_ratio = 4 / 3

        # Привязка к рамке (устанавливается frame_containment)
        self._frame = None

        self.setPos(
            x,
            y,
        )

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

        self.setAcceptHoverEvents(True)

        self.setPen(
            QPen(
                QColor("#D8D8D8"),
                1.0,
            )
        )

        self.setBrush(
            QBrush(
                QColor(self.card_color)
            )
        )

        self.title_item = None
        self.body_item = None

        # Стрелки, привязанные к этой карточке
        self.arrows = []

        self.setup_card()

    # =========================================================
    # COLOR
    # =========================================================

    @staticmethod
    def _normalize_color(color):
        if isinstance(color, QColor):
            return color.name(
                QColor.NameFormat.HexArgb
            )

        if color is None:
            return "#FFFFFFFF"

        color = str(color)

        qcolor = QColor(color)

        if qcolor.isValid():
            return qcolor.name(
                QColor.NameFormat.HexArgb
            )

        return "#FFFFFFFF"

    def set_card_color(
        self,
        color,
    ):
        self.card_color = self._normalize_color(
            color
        )

        self.setBrush(
            QBrush(
                QColor(self.card_color)
            )
        )

        self.update()

    def get_card_color(self):
        return self._normalize_color(
            self.card_color
        )

    # =========================================================
    # SETUP
    # =========================================================

    def setup_card(self):

        if self.card_type == "comment":
            self.setup_comment_card()

        elif self.card_type == "heading":
            self.setup_heading_card()

        elif self.card_type == "image_text":
            self.setup_image_text_card()

        elif self.card_type == "color":
            self.setup_color_card()

        else:
            self.setup_text_card()

    def setup_text_card(self):

        self.body_item = EditableText(
            self.body_text,
            self,
        )

        self.body_item.setPos(
            12,
            12,
        )

        self.body_item.setTextWidth(
            max(
                100,
                self.rect().width() - 24,
            )
        )

    def setup_comment_card(self):

        self.title_item = EditableText(
            self.title_text,
            self,
        )

        self.title_item.setPos(
            50,
            10,
        )

        self.body_item = EditableText(
            self.body_text,
            self,
        )

        self.body_item.setPos(
            12,
            38,
        )

        self.body_item.setTextWidth(
            max(
                100,
                self.rect().width() - 24,
            )
        )

    def setup_heading_card(self):

        self.title_item = EditableText(
            self.title_text,
            self,
        )

        self.title_item.setPos(
            16,
            12,
        )

        self.body_item = EditableText(
            self.body_text,
            self,
        )

        self.body_item.setPos(
            16,
            55,
        )

        self.body_item.setTextWidth(
            max(
                100,
                self.rect().width() - 32,
            )
        )

    def setup_image_text_card(self):

        self.title_item = EditableText(
            self.title_text,
            self,
        )

        self.title_item.setPos(
            16,
            200,
        )

        self.body_item = EditableText(
            self.body_text,
            self,
        )

        self.body_item.setPos(
            16,
            240,
        )

        self.body_item.setTextWidth(
            max(
                100,
                self.rect().width() - 32,
            )
        )

    def setup_color_card(self):

        # Color cards don't display text.
        pass

    # =========================================================
    # IMAGE
    # =========================================================

    def set_image(
        self,
        pixmap,
        image_path="",
    ):

        if pixmap is None:
            return

        if pixmap.isNull():
            return

        self.image_pixmap = pixmap
        self.image_path = image_path

        self.set_image_aspect_ratio(
            pixmap.width(),
            pixmap.height(),
        )

        self.update_image_text_height()
        self.update()

    def set_image_aspect_ratio(
        self,
        image_width,
        image_height,
    ):

        if image_width <= 0:
            return

        if image_height <= 0:
            return

        self.image_aspect_ratio = (
            image_width / image_height
        )

        self.update_image_text_height()

    # =========================================================
    # GEOMETRY
    # =========================================================

    def boundingRect(self):

        return self.rect().adjusted(
            -2,
            -2,
            2,
            2,
        )

    # =========================================================
    # ARROWS
    # =========================================================

    def itemChange(
        self,
        change,
        value,
    ):

        # Snap-логика: когда карточка движется — ищем
        # близкие края/центры других карточек и прилипаем.
        try:
            from PySide6.QtWidgets import QGraphicsItem

            if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
                self._apply_snap()
        except Exception:
            pass

        return super().itemChange(
            change,
            value,
        )

    # =========================================================
    # SNAP GUIDES
    # =========================================================

    SNAP_THRESHOLD = 5.0

    def _apply_snap(self):
        """
        Проверяет ближайшие края и центры других карточек
        и корректирует позицию для выравнивания.
        """

        scene = self.scene()

        if scene is None:
            print(f"[SNAP] no scene")
            return

        # Если мы внутри рамки и рамка двигает нас — не снапим
        if getattr(self, "_inside_frame_move", False):
            return

        my_rect = self.sceneBoundingRect()

        my_xs = [
            my_rect.left(),
            my_rect.center().x(),
            my_rect.right(),
        ]
        my_ys = [
            my_rect.top(),
            my_rect.center().y(),
            my_rect.bottom(),
        ]

        best_dx = None
        best_dy = None
        best_x_guide = None
        best_y_guide = None

        # Собираем snap-линии от всех других карточек
        for other in scene.items():
            if other is self:
                continue

            # Игнорируем стрелки, рамки, overlay
            if not hasattr(other, "card_id"):
                continue

            if other.scene() is None:
                continue

            other_rect = other.sceneBoundingRect()

            other_xs = [
                other_rect.left(),
                other_rect.center().x(),
                other_rect.right(),
            ]
            other_ys = [
                other_rect.top(),
                other_rect.center().y(),
                other_rect.bottom(),
            ]

            # Ищем минимальный dx по X
            for mx in my_xs:
                for ox in other_xs:
                    dx = ox - mx

                    if abs(dx) <= self.SNAP_THRESHOLD:
                        if best_dx is None or abs(dx) < abs(best_dx):
                            best_dx = dx
                            best_x_guide = ox

            # Ищем минимальный dy по Y
            for my in my_ys:
                for oy in other_ys:
                    dy = oy - my

                    if abs(dy) <= self.SNAP_THRESHOLD:
                        if best_dy is None or abs(dy) < abs(best_dy):
                            best_dy = dy
                            best_y_guide = oy

        # Применяем snap
        moved = False

        if best_dx is not None and abs(best_dx) > 0.01:
            pos = self.pos()
            self.setPos(pos.x() + best_dx, pos.y())
            moved = True

        if best_dy is not None and abs(best_dy) > 0.01:
            pos = self.pos()
            self.setPos(pos.x(), pos.y() + best_dy)
            moved = True

        # Показываем линии-направляющие через Canvas
        try:
            view = scene.views()[0] if scene.views() else None

    
            if view is not None:
                v_lines = [best_x_guide] if best_x_guide is not None else []
                h_lines = [best_y_guide] if best_y_guide is not None else []


                setter = getattr(view, "set_snap_guides", None)


                if callable(setter):
                    setter(vertical=v_lines, horizontal=h_lines)

        except Exception as exc:
            print(f"[SNAP-GUIDE] ERROR: {exc!r}")

    def clear_snap_guides(self):
        """
        Убирает линии-направляющие.
        Вызывается когда карточка отпущена.
        """

        scene = self.scene()

        if scene is None:
            return

        try:
            from ...canvas.snap_overlay import SnapOverlay

            for it in scene.items():
                if isinstance(it, SnapOverlay):
                    it.clear_guides()
                    break
        except Exception:
            pass

    def set_card_size(
        self,
        width,
        height,
    ):

        if self.card_type == "comment":

            width = max(
                width,
                self.MIN_COMMENT_WIDTH,
            )

            height = max(
                height,
                self.MIN_COMMENT_HEIGHT,
            )

        elif self.card_type == "heading":

            width = max(
                width,
                self.MIN_HEADING_WIDTH,
            )

            height = max(
                height,
                self.MIN_HEADING_HEIGHT,
            )

        elif self.card_type == "image_text":

            width = max(
                width,
                self.MIN_IMAGE_WIDTH,
            )

            height = max(
                height,
                self.MIN_IMAGE_HEIGHT,
            )

        elif self.card_type == "color":

            width = max(
                width,
                self.MIN_COLOR_WIDTH,
            )

            height = max(
                height,
                self.MIN_COLOR_HEIGHT,
            )

        else:

            width = max(
                width,
                self.MIN_TEXT_WIDTH,
            )

            height = max(
                height,
                self.MIN_TEXT_HEIGHT,
            )

        self.prepareGeometryChange()

        self.setRect(
            0,
            0,
            width,
            height,
        )

        self.update_height()

        self.update()

    def update_layout(self):

        if self.body_item is not None:

            self.body_item.setTextWidth(
                max(
                    100,
                    self.rect().width() - 24,
                )
            )

    def update_height(self):

        if self.card_type == "comment":
            self.update_comment_height()

        elif self.card_type == "heading":
            self.update_heading_height()

        elif self.card_type == "image_text":
            self.update_image_text_height()

    def update_comment_height(self):

        if self.body_item is None:
            return

        document = self.body_item.document()

        text_width = max(
            50,
            self.rect().width() - 24,
        )

        document.setTextWidth(text_width)

        body_height = document.size().height()

        new_height = max(
            self.MIN_COMMENT_HEIGHT,
            48 + body_height + 12,
        )

        current_height = self.rect().height()

        if abs(new_height - current_height) < 1:
            return

        self.prepareGeometryChange()

        self.setRect(
            0,
            0,
            self.rect().width(),
            new_height,
        )

        self.update()

    def update_heading_height(self):

        if self.title_item is None or self.body_item is None:
            return

        width = self.rect().width()

        text_width = max(
            50,
            width - 32,
        )

        self.title_item.setTextWidth(text_width)
        self.body_item.setTextWidth(text_width)

        title_doc = self.title_item.document()
        body_doc = self.body_item.document()

        title_doc.setTextWidth(text_width)
        body_doc.setTextWidth(text_width)

        title_height = title_doc.size().height()
        body_height = body_doc.size().height()

        new_height = max(
            self.MIN_HEADING_HEIGHT,
            12 + title_height + 30 + body_height + 20,
        )

        current_height = self.rect().height()

        if abs(new_height - current_height) < 1:
            return

        self.prepareGeometryChange()

        self.setRect(
            0,
            0,
            width,
            new_height,
        )

        self.update()

    def update_image_text_height(self):

        if self.body_item is None:
            return

        width = max(
            self.MIN_IMAGE_WIDTH,
            self.rect().width(),
        )

        text_width = max(
            50,
            width - 32,
        )

        if self.title_item is not None:
            self.title_item.setTextWidth(text_width)

        self.body_item.setTextWidth(text_width)

        image_width = max(
            100,
            width - 28,
        )

        image_height = (
            image_width
            / max(
                0.01,
                self.image_aspect_ratio,
            )
        )

        title_height = 0

        if self.title_item is not None:

            self.title_item.document().setTextWidth(
                text_width
            )

            title_height = (
                self.title_item.document().size().height()
            )

        self.body_item.document().setTextWidth(
            text_width
        )

        body_height = (
            self.body_item.document().size().height()
        )

        new_height = (
            14
            + image_height
            + 12
            + title_height
            + 6
            + body_height
            + 18
        )

        new_height = max(
            self.MIN_IMAGE_HEIGHT,
            new_height,
        )

        current_height = self.rect().height()

        if abs(new_height - current_height) >= 1:

            self.prepareGeometryChange()

            self.setRect(
                0,
                0,
                width,
                new_height,
            )

        self.update()

    # =========================================================
    # CONNECTION
    # =========================================================

    def has_connection_point(self):
        return has_connection_point(self)

    def connection_point(self):
        return connection_point(self)

    # =========================================================
    # RESIZE
    # =========================================================

    def resize_zone(self, pos):
        return resize_zone(self, pos)

    # =========================================================
    # TEXT HIT-TEST
    # =========================================================

    def _find_editable_at(
        self,
        scene_pos,
    ):

        for child in self.childItems():

            if not isinstance(
                child,
                EditableText,
            ):
                continue

            local_pos = child.mapFromScene(
                scene_pos
            )

            if child.contains(local_pos):
                return child

        return None

    def _disable_all_editing(self):

        for child in self.childItems():

            if isinstance(
                child,
                EditableText,
            ):

                if child.is_editing_enabled():
                    child.set_editing_enabled(False)

    # =========================================================
    # MOUSE
    # =========================================================

    def hoverMoveEvent(
        self,
        event,
    ):

        update_connection_hover(
            self,
            event.pos(),
        )

        self.update()

        super().hoverMoveEvent(event)

    def hoverLeaveEvent(
        self,
        event,
    ):

        self.connection_hovered = False
        self.hover_point_index = None

        self.update()

        super().hoverLeaveEvent(event)

    def mousePressEvent(
        self,
        event,
    ):

        hit_text = self._find_editable_at(
            event.scenePos()
        )

        if (
            hit_text is None
            or not hit_text.is_editing_enabled()
        ):

            self._disable_all_editing()

        if (
            event.button()
            == Qt.MouseButton.LeftButton
            and self.resize_zone(event.pos()
            )
        ):

            start_resize(
                self,
                event.pos(),
            )

            event.accept()
            return

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(
        self,
        event,
    ):

        hit_text = self._find_editable_at(
            event.scenePos()
        )

        if hit_text is not None:

            hit_text.set_editing_enabled(
                True
            )

            event.accept()
            return

        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(
        self,
        event,
    ):

        if self.resizing:

            size = calculate_resize(
                self,
                event.pos(),
            )

            if size is not None:

                width, height = size

                self.set_card_size(
                    width,
                    height,
                )

            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(
        self,
        event,
    ):

        # Убираем линии-направляющие после отпускания
        try:
            scene = self.scene()

            if scene is not None:
                views = scene.views()

                if views:
                    view = views[0]
                    clearer = getattr(view, "clear_snap_guides", None)

                    if callable(clearer):
                        clearer()
        except Exception:
            pass

        if self.resizing:

            finish_resize(self)

            event.accept()
            return

        super().mouseReleaseEvent(event)

        # =====================================================
        # FRAME MEMBERSHIP
        # =====================================================

        try:

            from ...canvas.frame_containment import (
                update_item_membership,
            )

            update_item_membership(
                self,
                self.scene(),
            )

        except Exception as exc:

            print(
                f"[FRAME] membership update failed: {exc!r}"
            )

    # =========================================================
    # CONTEXT MENU
    # =========================================================

    def contextMenuEvent(
        self,
        event,
    ):

        menu = QMenu()

        replace_image_action = None
        remove_image_action = None

        if self.card_type == "image_text":

            replace_image_action = menu.addAction(
                "Заменить изображение"
            )

            remove_image_action = menu.addAction(
                "Удалить изображение"
            )

            menu.addSeparator()

        add_arrow_action = menu.addAction(
            "Добавить стрелку"
        )

        menu.addSeparator()

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

        if action == replace_image_action:
            self.replace_image()

        elif action == remove_image_action:
            self.remove_image()

        elif action == add_arrow_action:

            if (
                self.scene()
                and self.scene().views()
            ):

                view = self.scene().views()[0]

                start_arrow = getattr(
                    view,
                    "start_arrow_from",
                    None,
                )

                if start_arrow:
                    start_arrow(self)

        elif action == change_color_action:

            view = None

            if (
                self.scene()
                and self.scene().views()
            ):
                view = self.scene().views()[0]

            if view is not None:

                main_window = getattr(
                    view,
                    "main_window",
                    None,
                )

                if main_window is not None:

                    from ...canvas.color import (
                        _show_color_palette,
                    )

                    _show_color_palette(
                        main_window.canvas,
                        self,
                    )

        elif action == delete_action:

            if self.scene():

                views = self.scene().views()

                if views:

                    view = views[0]

                    main_window = getattr(
                        view,
                        "main_window",
                        None,
                    )

                    if main_window is not None:

                        view.delete_item(
                            self
                        )

        event.accept()

    def replace_image(self):

        if self.card_type != "image_text":
            return

        if not self.scene():
            return

        views = self.scene().views()

        if not views:
            return

        view = views[0]

        main_window = getattr(
            view,
            "main_window",
            None,
        )

        if main_window is None:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            main_window,
            "Выберите новое изображение",
            "",
            "Изображения (*.png *.jpg *.jpeg *.webp *.bmp);;Все файлы (*)",
        )

        if not file_path:
            return

        pixmap = QPixmap(file_path)

        if pixmap.isNull():

            main_window.update_status(
                "Не удалось загрузить изображение"
            )

            return

        project_name = getattr(
            main_window,
            "project_name",
            "",
        )

        if not project_name:

            main_window.update_status(
                "Сначала создайте или откройте проект"
            )

            return

        project_folder = ensure_project_folder(
            project_name
        )

        images_folder = os.path.join(
            project_folder,
            "images",
        )

        os.makedirs(
            images_folder,
            exist_ok=True,
        )

        extension = os.path.splitext(
            file_path
        )[1].lower()

        if not extension:
            extension = ".png"

        filename = str(uuid.uuid4()) + extension

        destination = os.path.join(
            images_folder,
            filename,
        )

        try:

            shutil.copy2(
                file_path,
                destination,
            )

        except OSError:

            main_window.update_status(
                "Не удалось скопировать изображение"
            )

            return

        self.image_pixmap = pixmap

        self.image_path = os.path.join(
            "images",
            filename,
        ).replace(
            "\\",
            "/",
        )

        self.set_image_aspect_ratio(
            pixmap.width(),
            pixmap.height(),
        )

        self.update_image_text_height()
        self.update()

        main_window.canvas.save_board()
        main_window.update_status(
            "Изображение заменено"
        )

    def remove_image(self):

        if self.card_type != "image_text":
            return

        if not self.scene():
            return

        views = self.scene().views()

        if not views:
            return

        view = views[0]

        main_window = getattr(
            view,
            "main_window",
            None,
        )

        if main_window is None:
            return

        self.image_pixmap = QPixmap()
        self.image_path = ""
        self.image_aspect_ratio = 4 / 3

        self.update_image_text_height()
        self.update()

        main_window.canvas.save_board()
        main_window.update_status(
            "Изображение удалено"
        )

    # =========================================================
    # PAINT
    # =========================================================

    def paint(
        self,
        painter,
        option,
        widget=None,
    ):

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        rect = self.rect()

        # Shadow
        shadow_rect = rect.adjusted(
            3,
            3,
            3,
            3,
        )

        painter.setPen(
            Qt.PenStyle.NoPen
        )

        painter.setBrush(
            QBrush(
                QColor(
                    0,
                    0,
                    0,
                    20,
                )
            )
        )

        painter.drawRoundedRect(
            shadow_rect,
            8,
            8,
        )

        # Card background
        painter.setPen(
            QPen(
                QColor("#D8D8D8"),
                1,
            )
        )

        painter.setBrush(
            QBrush(
                QColor(self.card_color)
            )
        )

        painter.drawRoundedRect(
            rect,
            8,
            8,
        )

        # Card-specific content
        self.paint_content(
            painter,
            rect,
        )

        # Connection point
        paint_connection_point(
            self,
            painter,
        )

    def paint_content(
        self,
        painter,
        rect,
    ):
        """
        Subclasses override this to draw their specific content.
        Default: draw image for image_text.
        """

        if self.card_type == "image_text":
            self.paint_image(
                painter,
                rect,
            )

    def paint_image(
        self,
        painter,
        rect,
    ):

        image_width = max(
            100,
            rect.width() - 28,
        )

        image_height = (
            image_width
            / max(
                0.01,
                self.image_aspect_ratio,
            )
        )

        image_rect = rect.adjusted(
            14,
            14,
            -14,
            0,
        )

        image_rect.setHeight(
            image_height
        )

        if self.image_pixmap.isNull():

            painter.setBrush(
                QColor(
                    232,
                    232,
                    227,
                )
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

            painter.drawRect(
                image_rect
            )

            painter.setPen(
                QColor(
                    145,
                    145,
                    140,
                )
            )

            painter.setFont(
                painter.font()
            )

            painter.drawText(
                image_rect,
                Qt.AlignmentFlag.AlignCenter,
                "Изображение",
            )

        else:

            scaled = self.image_pixmap.scaled(
                int(image_rect.width()),
                int(image_rect.height()),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            image_x = (
                image_rect.x()
                + (
                    image_rect.width()
                    - scaled.width()
                )
                / 2
            )

            image_y = (
                image_rect.y()
                + (
                    image_rect.height()
                    - scaled.height()
                )
                / 2
            )

            painter.drawPixmap(
                int(image_x),
                int(image_y),
                scaled,
            )