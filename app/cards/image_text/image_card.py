from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QPen, QFont

from ..base.card import Card
from ..base.typography import apply_to_editable, body_font


class ImageTextCard(Card):

    IMAGE_SIDE_MARGIN = 14
    IMAGE_TOP_MARGIN = 14
    IMAGE_TEXT_MARGIN = 12
    IMAGE_TITLE_GAP = 12
    IMAGE_BODY_GAP = 6
    IMAGE_BOTTOM_MARGIN = 18

    def __init__(
        self,
        title="Заголовок",
        text="",
        x=0,
        y=0,
        width=360,
        height=420,
        color="#FFFFFF",
    ):
        super().__init__(
            x=x,
            y=y,
            width=max(width, self.MIN_IMAGE_WIDTH),
            height=max(height, self.MIN_IMAGE_HEIGHT),
            card_type="image_text",
            title=title,
            body=text,
            color=color,
        )

    # =========================================================
    # SETUP
    # =========================================================

    def setup_card(self):

        from ..base.editable_text import EditableText

        self.title_item = EditableText(
            self.title_text,
            self,
        )

        apply_to_editable(self.title_item, "title")
        self.title_item.setDefaultTextColor(QColor("#202020"))

        self.body_item = EditableText(
            self.body_text,
            self,
        )

        apply_to_editable(self.body_item, "body")
        self.body_item.setDefaultTextColor(QColor("#555555"))

        # Connect auto-height to BOTH title and body
        self.title_item.document().contentsChanged.connect(
            self.update_height
        )

        self.body_item.document().contentsChanged.connect(
            self.update_height
        )

        # Initial layout
        self.update_height()

    # =========================================================
    # HEIGHT + LAYOUT
    # =========================================================

    def update_height(self):

        if self.title_item is None or self.body_item is None:
            return

        width = max(
            self.MIN_IMAGE_WIDTH,
            self.rect().width(),
        )

        text_width = max(
            50,
            width
            - self.IMAGE_SIDE_MARGIN * 2
            - self.IMAGE_TEXT_MARGIN * 2,
        )

        self.title_item.setTextWidth(text_width)
        self.body_item.setTextWidth(text_width)

        # image height
        image_width = max(
            100,
            width - self.IMAGE_SIDE_MARGIN * 2,
        )

        image_height = (
            image_width / max(0.01, self.image_aspect_ratio)
        )

        # title height
        self.title_item.document().setTextWidth(text_width)
        title_height = max(
            22,
            self.title_item.document().size().height(),
        )

        # body height
        self.body_item.document().setTextWidth(text_width)
        body_height = max(
            20,
            self.body_item.document().size().height(),
        )

        # total height
        new_height = (
            self.IMAGE_TOP_MARGIN
            + image_height
            + self.IMAGE_TITLE_GAP
            + title_height
            + self.IMAGE_BODY_GAP
            + body_height
            + self.IMAGE_BOTTOM_MARGIN
        )

        new_height = max(
            self.MIN_IMAGE_HEIGHT,
            new_height,
        )

        # Y positions
        title_y = (
            self.IMAGE_TOP_MARGIN
            + image_height
            + self.IMAGE_TITLE_GAP
        )

        body_y = (
            title_y
            + title_height
            + self.IMAGE_BODY_GAP
        )

        text_x = (
            self.IMAGE_SIDE_MARGIN
            + self.IMAGE_TEXT_MARGIN
        )

        # Move title and body
        self.title_item.setPos(text_x, title_y)
        self.body_item.setPos(text_x, body_y)

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
    # PAINT
    # =========================================================

    def paint_content(self, painter, rect):

        image_width = max(
            100,
            rect.width() - self.IMAGE_SIDE_MARGIN * 2,
        )

        image_height = (
            image_width / max(0.01, self.image_aspect_ratio)
        )

        image_rect = rect.adjusted(
            self.IMAGE_SIDE_MARGIN,
            self.IMAGE_TOP_MARGIN,
            -self.IMAGE_SIDE_MARGIN,
            0,
        )

        image_rect.setHeight(image_height)

        if self.image_pixmap.isNull():

            painter.setBrush(QColor(232, 232, 227))
            painter.setPen(QPen(QColor(205, 205, 200), 1))

            painter.drawRect(image_rect)

            painter.setPen(QColor(145, 145, 140))
            painter.setFont(body_font())

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
                + (image_rect.width() - scaled.width()) / 2
            )

            image_y = (
                image_rect.y()
                + (image_rect.height() - scaled.height()) / 2
            )

            painter.drawPixmap(
                int(image_x),
                int(image_y),
                scaled,
            )