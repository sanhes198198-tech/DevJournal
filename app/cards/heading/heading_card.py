from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QPen

from ..base.card import Card
from ..base.typography import apply_to_editable


class HeadingCard(Card):

    HEADING_SIDE_MARGIN = 10
    HEADING_TEXT_MARGIN = 12
    HEADING_GAP = 8
    HEADING_HEADER_MIN_HEIGHT = 44
    HEADING_BODY_MIN_HEIGHT = 46

    def __init__(
        self,
        title="",
        text="",
        x=0,
        y=0,
        width=340,
        height=150,
        color="#FFFFFF",
    ):
        super().__init__(
            x=x,
            y=y,
            width=max(width, self.MIN_HEADING_WIDTH),
            height=max(height, self.MIN_HEADING_HEIGHT),
            card_type="heading",
            title=title,
            body=text,
            color=color,
        )

    # =========================================================
    # SETUP
    # =========================================================

    def setup_card(self):

        self.title_item = self._make_editable(
            self.title_text,
        )

        apply_to_editable(self.title_item, "title")
        self.title_item.setDefaultTextColor(QColor("#444444"))

        self.body_item = self._make_editable(
            self.body_text,
        )

        apply_to_editable(self.body_item, "body")
        self.body_item.setDefaultTextColor(QColor("#444444"))

        self.update_layout()

        self.title_item.document().contentsChanged.connect(
            self.update_height
        )

        self.body_item.document().contentsChanged.connect(
            self.update_height
        )

        self.update_height()

    def _make_editable(self, text):
        from ..base.editable_text import EditableText
        return EditableText(text, self)

    # =========================================================
    # LAYOUT
    # =========================================================

    def update_layout(self):

        if self.title_item is None or self.body_item is None:
            return

        width = self.rect().width()

        text_width = max(
            50,
            width
            - self.HEADING_SIDE_MARGIN * 2
            - self.HEADING_TEXT_MARGIN * 2,
        )

        self.title_item.setTextWidth(text_width)
        self.body_item.setTextWidth(text_width)

    # =========================================================
    # HEIGHT
    # =========================================================

    def update_height(self):

        if self.title_item is None or self.body_item is None:
            return

        width = self.rect().width()

        text_width = max(
            50,
            width
            - self.HEADING_SIDE_MARGIN * 2
            - self.HEADING_TEXT_MARGIN * 2,
        )

        self.title_item.setTextWidth(text_width)
        self.body_item.setTextWidth(text_width)

        title_doc = self.title_item.document()
        body_doc = self.body_item.document()

        title_doc.setTextWidth(text_width)
        body_doc.setTextWidth(text_width)

        title_height = title_doc.size().height()
        body_height = body_doc.size().height()

        header_height = max(
            self.HEADING_HEADER_MIN_HEIGHT,
            title_height + self.HEADING_TEXT_MARGIN * 2,
        )

        body_block_height = max(
            self.HEADING_BODY_MIN_HEIGHT,
            body_height + self.HEADING_TEXT_MARGIN * 2,
        )

        new_height = (
            self.HEADING_SIDE_MARGIN
            + header_height
            + self.HEADING_GAP
            + body_block_height
            + self.HEADING_SIDE_MARGIN
        )

        new_height = max(
            self.MIN_HEADING_HEIGHT,
            new_height,
        )

        header_y = self.HEADING_SIDE_MARGIN

        body_y = (
            header_y
            + header_height
            + self.HEADING_GAP
        )

        self.title_item.setPos(
            self.HEADING_SIDE_MARGIN + self.HEADING_TEXT_MARGIN,
            header_y + self.HEADING_TEXT_MARGIN,
        )

        self.body_item.setPos(
            self.HEADING_SIDE_MARGIN + self.HEADING_TEXT_MARGIN,
            body_y + self.HEADING_TEXT_MARGIN,
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
    # PAINT
    # =========================================================

    def paint_content(self, painter, rect):

        if self.title_item is None or self.body_item is None:
            return

        text_width = max(
            50,
            rect.width()
            - self.HEADING_SIDE_MARGIN * 2
            - self.HEADING_TEXT_MARGIN * 2,
        )

        title_doc = self.title_item.document()

        title_doc.setTextWidth(text_width)

        title_height = title_doc.size().height()

        header_height = max(
            self.HEADING_HEADER_MIN_HEIGHT,
            title_height + self.HEADING_TEXT_MARGIN * 2,
        )

        # --- рамка только вокруг заголовка ---

        header_rect = rect.adjusted(
            self.HEADING_SIDE_MARGIN,
            self.HEADING_SIDE_MARGIN,
            -self.HEADING_SIDE_MARGIN,
            0,
        )

        header_rect.setHeight(header_height)

        painter.setBrush(QColor(self.card_color))

        # Полупрозрачная рамка — альфа 30
        painter.setPen(
            QPen(
                QColor(0, 0, 0, 30),
                1,
            )
        )

        painter.drawRect(header_rect)