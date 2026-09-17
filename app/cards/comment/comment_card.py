from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QColor,
    QBrush,
    QPen,
    QPainter,
)

from ..base.card import Card
from ..base.editable_text import EditableText
from ..base.typography import apply_to_editable


class CommentCard(Card):
    """
    Карточка комментария.

    Отвечает за внешний вид,
    текст и автоматическую высоту комментария.
    """

    MIN_WIDTH = 250
    MIN_HEIGHT = 70

    AVATAR_SIZE = 38

    TITLE_X = 61
    TITLE_Y = 9

    BODY_X = 61
    BODY_Y = 29

    TEXT_RIGHT_MARGIN = 76

    def __init__(
        self,
        title="",
        text="",
        width=320,
        height=70,
        color="#FFFFFF",
    ):
        super().__init__(
            x=0,
            y=0,
            width=max(width, self.MIN_WIDTH),
            height=max(height, self.MIN_HEIGHT),
            card_type="comment",
            title=title,
            body=text,
            color=color,
        )

    # ==============================================================
    # SETUP
    # ==============================================================

    def setup_comment_card(self):
        """
        Создает и настраивает элементы комментария.
        """

        if self.title_item is None:
            self.title_item = EditableText(
                self.title_text,
                self,
            )

        if self.body_item is None:
            self.body_item = EditableText(
                self.body_text,
                self,
            )

        if self.title_item.toPlainText() in (
            "",
            "Комментарий",
        ):
            self.title_item.setPlainText(
                "Автор"
            )

        # ----------------------------------------------------------
        # Имя автора
        # ----------------------------------------------------------

        apply_to_editable(self.title_item, "comment_title")

        self.title_item.setDefaultTextColor(
            QColor("#444444")
        )

        # ----------------------------------------------------------
        # Текст комментария
        # ----------------------------------------------------------

        apply_to_editable(self.body_item, "body")

        self.body_item.setDefaultTextColor(
            QColor("#444444")
        )

        # ----------------------------------------------------------
        # Layout
        # ----------------------------------------------------------

        self.update_comment_layout()

        # ----------------------------------------------------------
        # Автоматическая высота
        # ----------------------------------------------------------

        self.body_item.document().contentsChanged.connect(
            self.update_comment_height
        )

        self.update_comment_height()

    # ==============================================================
    # LAYOUT
    # ==============================================================

    def update_comment_layout(self):
        """
        Обновляет положение текстовых элементов.
        """

        width = self.rect().width()

        text_width = max(
            50,
            width - self.TEXT_RIGHT_MARGIN,
        )

        self.title_item.setTextWidth(
            text_width
        )

        self.body_item.setTextWidth(
            text_width
        )

        self.title_item.setPos(
            self.TITLE_X,
            self.TITLE_Y,
        )

        self.body_item.setPos(
            self.BODY_X,
            self.BODY_Y,
        )

    # ==============================================================
    # HEIGHT
    # ==============================================================

    def update_comment_height(self):
        """
        Автоматически увеличивает высоту комментария,
        если текста становится больше.
        """

        if self.body_item is None:
            return

        document = self.body_item.document()

        text_width = max(
            50,
            self.rect().width()
            - self.TEXT_RIGHT_MARGIN,
        )

        document.setTextWidth(
            text_width
        )

        body_height = document.size().height()

        new_height = max(
            self.MIN_HEIGHT,
            29
            + body_height
            + 14,
        )

        current_height = self.rect().height()

        if abs(
            new_height - current_height
        ) < 1:
            return

        self.prepareGeometryChange()

        self.setRect(
            0,
            0,
            self.rect().width(),
            new_height,
        )

        self.update()

    # ==============================================================
    # RESIZE
    # ==============================================================

    def set_card_size(
        self,
        width,
        height,
    ):
        """
        Изменяет ширину комментария.

        Высота рассчитывается автоматически.
        """

        width = max(
            self.MIN_WIDTH,
            width,
        )

        self.prepareGeometryChange()

        self.setRect(
            0,
            0,
            width,
            self.rect().height(),
        )

        self.update_comment_layout()
        self.update_comment_height()

        self.update()

    # ==============================================================
    # PAINT
    # ==============================================================

    def paint(
        self,
        painter,
        option,
        widget=None,
    ):
        """
        Отрисовывает комментарий.
        """

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        rect = self.rect()

        radius = min(
            28,
            rect.height() / 2,
        )

        # ----------------------------------------------------------
        # Тень
        # ----------------------------------------------------------

        shadow_rect = rect.adjusted(
            3,
            5,
            3,
            6,
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
                    22,
                )
            )
        )

        painter.drawRoundedRect(
            shadow_rect,
            radius,
            radius,
        )

        # ----------------------------------------------------------
        # Фон
        # ----------------------------------------------------------

        painter.setBrush(
            QBrush(
                QColor(
                    self.card_color
                )
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
                        220,
                        220,
                        216,
                    ),
                    1,
                )
            )

        painter.drawRoundedRect(
            rect,
            radius,
            radius,
        )

        # ----------------------------------------------------------
        # Аватар
        # ----------------------------------------------------------

        avatar_rect = QRectF(
            12,
            11,
            self.AVATAR_SIZE,
            self.AVATAR_SIZE,
        )

        painter.setPen(
            Qt.PenStyle.NoPen
        )

        painter.setBrush(
            QBrush(
                QColor(
                    245,
                    245,
                    240,
                )
            )
        )

        painter.drawEllipse(
            avatar_rect
        )

    def contextMenuEvent(self, event):

        from PySide6.QtWidgets import QMenu

        menu = QMenu()

        change_color_action = menu.addAction("Изменить цвет")
        menu.addSeparator()
        delete_action = menu.addAction("Удалить")

        action = menu.exec(event.screenPos())

        if action == change_color_action:

            view = None

            if self.scene() and self.scene().views():
                view = self.scene().views()[0]

            if view is not None:

                main_window = getattr(view, "main_window", None)

                if main_window is not None:

                    from ...canvas.color import _show_color_palette

                    _show_color_palette(
                        main_window.canvas,
                        self,
                    )

        elif action == delete_action:

            if self.scene():

                views = self.scene().views()

                if views:

                    view = views[0]

                    main_window = getattr(view, "main_window", None)

                    if main_window is not None:

                        view.delete_item(self)

        event.accept()