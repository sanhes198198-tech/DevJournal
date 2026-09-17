from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QPen, QPainter

from ..base.card import Card
from ..base.typography import apply_to_editable


class TextCard(Card):

    def __init__(
        self,
        title="Новая карточка",
        text="",
        x=0,
        y=0,
        width=280,
        height=180,
        color="#FFFFFF",
    ):
        super().__init__(
            x=x,
            y=y,
            width=max(width, self.MIN_TEXT_WIDTH),
            height=max(height, self.MIN_TEXT_HEIGHT),
            card_type="text",
            title=title,
            body=text,
            color=color,
        )

    # =========================================================
    # SETUP
    # =========================================================

    def setup_card(self):

        self.setup_text_card()

        apply_to_editable(self.body_item, "body")

        if self.body_item is not None:

            self.body_item.setDefaultTextColor(QColor("#444444"))

            self.body_item.document().contentsChanged.connect(
                self.update_height
            )

        self.update_height()

    # =========================================================
    # HEIGHT
    # =========================================================

    def update_height(self):

        if self.body_item is None:
            return

        width = self.rect().width()

        text_width = max(
            50,
            width - 24,
        )

        self.body_item.document().setTextWidth(text_width)

        body_height = self.body_item.document().size().height()

        new_height = max(
            self.MIN_TEXT_HEIGHT,
            12 + body_height + 12,
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

    # =========================================================
    # PAINT
    # =========================================================

    def paint_content(self, painter, rect):
        # Nothing special — background + border are drawn by base.
        pass