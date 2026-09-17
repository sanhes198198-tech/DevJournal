"""
Frame container (FrameItem) for DevJournal.
"""

import uuid

from PySide6.QtCore import Qt, QRectF, QTimer, QPointF
from PySide6.QtGui import QPen, QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsItem,
    QMenu,
    QInputDialog,
)

from .frame_title import (
    create_frame_title,
    update_title_width,
)

from .frame_resize import (
    resize_zone,
    start_resize,
    apply_resize,
    finish_resize,
    cursor_for_zone,
    autosize_to_members,
)

from .frame_overlay import create_frame_overlay


TITLE_DEFAULT = "\u0420\u0430\u043c\u043a\u0430"
LABEL_RENAME = "\u041f\u0435\u0440\u0435\u0438\u043c\u0435\u043d\u043e\u0432\u0430\u0442\u044c"
LABEL_DELETE = "\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u0440\u0430\u043c\u043a\u0443"
LABEL_RENAME_DIALOG = "\u041f\u0435\u0440\u0435\u0438\u043c\u0435\u043d\u043e\u0432\u0430\u043d\u0438\u0435 \u0440\u0430\u043c\u043a\u0438"
LABEL_NEW_NAME = "\u041d\u043e\u0432\u043e\u0435 \u0438\u043c\u044f:"
LABEL_FRAME_ADDED = "\u0414\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u0430 \u0440\u0430\u043c\u043a\u0430"
LABEL_CHANGE_COLOR = "\u0426\u0432\u0435\u0442 \u0440\u0430\u043c\u043a\u0438"
LABEL_AUTOSIZE = "\u041f\u043e\u0434\u043e\u0433\u043d\u0430\u0442\u044c \u043f\u043e\u0434 \u0441\u043e\u0434\u0435\u0440\u0436\u0438\u043c\u043e\u0435"
LABEL_FILL_MENU = "\u0426\u0432\u0435\u0442 \u0444\u043e\u043d\u0430"
LABEL_FILL_TRANSPARENT = "\u041f\u0440\u043e\u0437\u0440\u0430\u0447\u043d\u044b\u0439"
LABEL_FILL_WHITE = "\u0411\u0435\u043b\u044b\u0439"
LABEL_FILL_GRAY = "\u0421\u0435\u0440\u044b\u0439"
LABEL_FILL_BLACK = "\u0427\u0451\u0440\u043d\u044b\u0439"
LABEL_LOCK = "\u0417\u0430\u0431\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0440\u0430\u043c\u043a\u0443"
LABEL_UNLOCK = "\u0420\u0430\u0437\u0431\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0440\u0430\u043c\u043a\u0443"


DEFAULT_FRAME_COLOR = "#B0B0B0"
DEFAULT_FRAME_FILL = "transparent"

LOCKED_BORDER_COLOR = QColor("#666666")


class FrameItem(QGraphicsRectItem):

    DEFAULT_WIDTH = 400.0
    DEFAULT_HEIGHT = 300.0
    FRAME_Z = -100.0

    BORDER_NORMAL = QColor("#B0B0B0")
    BORDER_SELECTED = QColor("#4F7CFF")
    BORDER_WIDTH = 2.0

    FILL_TRANSPARENT = QColor(0, 0, 0, 0)
    FILL_WHITE = QColor(255, 255, 255, 60)
    FILL_GRAY = QColor(180, 180, 180, 90)
    FILL_BLACK = QColor(30, 30, 30, 120)

    TITLE_COLOR = QColor("#7A7A7A")
    TITLE_FONT_SIZE = 10
    TITLE_PADDING = 8.0
    TITLE_HEIGHT = 22.0

    def __init__(
        self,
        x=0.0,
        y=0.0,
        width=DEFAULT_WIDTH,
        height=DEFAULT_HEIGHT,
        title=None,
        frame_id=None,
        frame_color=None,
        frame_fill=None,
        locked=False,
    ):
        super().__init__(x, y, width, height)

        if frame_id is None:
            frame_id = str(uuid.uuid4())

        if title is None:
            title = TITLE_DEFAULT

        if frame_color is None:
            frame_color = DEFAULT_FRAME_COLOR

        if frame_fill is None:
            frame_fill = DEFAULT_FRAME_FILL

        self.frame_id = frame_id
        self.title = title
        self.frame_color = frame_color
        self.frame_fill = frame_fill
        self.locked = bool(locked)
        self._members = []

        self.title_item = None

        try:
            self.title_item = create_frame_title(title, self)

            try:
                from .frame_title import connect_title_changes

                connect_title_changes(self)
            except Exception:
                pass

        except Exception:
            self.title_item = None

        self.resizing = False
        self.resize_zone_name = None
        self.resize_start_pos = None
        self.resize_start_rect = None
        self.resize_start_frame_pos = None

        self.overlay = None

        self._last_move_pos = None
        self._moving_with_members = False

        self.setZValue(self.FRAME_Z)

        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

        self.setAcceptHoverEvents(True)

        self._refresh_style()
        self._apply_lock_state()

        QTimer.singleShot(0, self._create_overlay)

    def _create_overlay(self):
        if self.overlay is not None:
            return

        if self.scene() is None:
            QTimer.singleShot(50, self._create_overlay)
            return

        try:
            self.overlay = create_frame_overlay(self)

            if self.overlay is not None:
                try:
                    self.overlay.setPos(self.pos())
                except Exception:
                    pass

                try:
                    self.overlay.setVisible(not self.locked)
                except Exception:
                    pass

        except Exception as exc:
            print(f"[FRAME] create_overlay failed: {exc!r}")
            self.overlay = None

        self._last_move_pos = None
        self._moving_with_members = False

    def _apply_lock_state(self):
        if self.locked:
            self.setFlag(
                QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable,
                False,
            )
            self.setFlag(
                QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable,
                False,
            )
            self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.setAcceptHoverEvents(False)

            try:
                self.setSelected(False)
            except Exception:
                pass

            if self.overlay is not None:
                try:
                    self.overlay.setVisible(False)
                except Exception:
                    pass

        else:
            self.setFlag(
                QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable,
                True,
            )
            self.setFlag(
                QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable,
                True,
            )
            self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
            self.setAcceptHoverEvents(True)

            if self.overlay is not None:
                try:
                    self.overlay.setVisible(True)
                except Exception:
                    pass

        self._refresh_style()
        self.update()

    def set_locked(self, locked):
        self.locked = bool(locked)
        self._apply_lock_state()

        if self.overlay is not None:
            try:
                self.overlay.update()
            except Exception:
                pass

    def is_locked(self):
        return self.locked

    def set_card_color(self, color):
        if color is None:
            return

        try:
            if isinstance(color, QColor):
                if color.isValid():
                    self.frame_color = color.name()
            else:
                q = QColor(str(color))

                if q.isValid():
                    self.frame_color = q.name()
        except Exception:
            return

        self._refresh_style()
        self.update()

    def get_card_color(self):
        return self.frame_color

    def _get_fill_color(self):
        name = self.frame_fill

        if name == "white":
            return self.FILL_WHITE

        if name == "gray":
            return self.FILL_GRAY

        if name == "black":
            return self.FILL_BLACK

        return self.FILL_TRANSPARENT

    def set_frame_fill(self, name):
        if name not in (
            "transparent",
            "white",
            "gray",
            "black",
        ):
            return

        self.frame_fill = name
        self._refresh_style()
        self.update()

    def _refresh_style(self):
        if self.locked:
            color = LOCKED_BORDER_COLOR

        elif self.isSelected():
            color = self.BORDER_SELECTED

        else:
            color = QColor(self.frame_color)

            if not color.isValid():
                color = self.BORDER_NORMAL

        self.setPen(
            QPen(color, self.BORDER_WIDTH, Qt.PenStyle.DashLine)
        )
        self.setBrush(QBrush(self._get_fill_color()))

    def itemChange(self, change, value):
        result = super().itemChange(change, value)

        if change in (
            QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged,
            QGraphicsItem.GraphicsItemChange.ItemSelectedChange,
        ):
            self._refresh_style()
            self.update()

            if self.overlay is not None:
                try:
                    self.overlay.update()
                except Exception:
                    pass

        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:

            # Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћвЂ“Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р РЋРЎвЂєР В Р вЂ Р В РІР‚С™Р вЂ™Р’ВР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р вЂ™Р’ВР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р Р†Р вЂљРЎС™Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’В°Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’ВµР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В РІР‚в„ўР вЂ™Р’В overlay.
            if self.overlay is not None:
                try:
                    self.overlay.setPos(value)
                    self.overlay.update()
                except Exception:
                    pass

            # Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћвЂ“Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р РЋРЎвЂєР В Р вЂ Р В РІР‚С™Р вЂ™Р’ВР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р вЂ™Р’ВР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р Р†Р вЂљРЎС™Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’В°Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’ВµР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В РІР‚в„ўР вЂ™Р’В _members Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В РІР‚в„ўР вЂ™Р’ВР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’ВµР В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р вЂ™Р’В Р В Р Р‹Р Р†Р вЂљРЎС™Р В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р В РІР‚В Р В Р’В Р Р†Р вЂљРЎв„ўР В Р Р‹Р Р†РІР‚С›РЎС›Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’Вµ Р В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р вЂ™Р’В Р В Р Р‹Р Р†Р вЂљРЎС™ Р В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р РЋРІвЂћСћР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’В°Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В РІР‚в„ўР вЂ™Р’ВР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р РЋРЎС™Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р РЋРЎвЂєР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В РІР‚В Р В Р вЂ Р В РІР‚С™Р РЋРІР‚С”Р В Р вЂ Р В РІР‚С™Р Р†Р вЂљРЎС™.
            if self._moving_with_members:
                try:
                    self._shift_members_to(value)
                except Exception as exc:
                    print(f"[FRAME] shift_members failed: {exc!r}")

        return result

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)

        if self.locked:
            try:
                rect = self.rect()

                icon_x = rect.right() - 22.0
                icon_y = rect.top() + 4.0

                painter.save()
                painter.setPen(QPen(QColor("#444444"), 1.4))
                painter.setBrush(QBrush(QColor("#F5F5F0")))

                painter.drawArc(
                    QRectF(icon_x + 3.0, icon_y, 10.0, 10.0),
                    0,
                    180 * 16,
                )

                painter.drawRect(
                    QRectF(icon_x, icon_y + 5.0, 16.0, 11.0)
                )

                painter.restore()

            except Exception:
                pass

    def hoverMoveEvent(self, event):
        zone = resize_zone(self, event.pos())
        cursor = cursor_for_zone(zone)

        try:
            if cursor:
                self.setCursor(getattr(Qt.CursorShape, cursor))
            else:
                self.setCursor(Qt.CursorShape.SizeAllCursor)
        except Exception:
            pass

        super().hoverMoveEvent(event)

    # ========================================================
    # MOVE WITH MEMBERS
    # ========================================================

    def _shift_members_to(self, new_frame_pos):
        if self._last_move_pos is None:
            return

        dx = new_frame_pos.x() - self._last_move_pos.x()
        dy = new_frame_pos.y() - self._last_move_pos.y()

        if abs(dx) < 0.01 and abs(dy) < 0.01:
            return

        # Собираем ВСЕ стрелки один раз перед сдвигом
        all_arrows = []

        for member in list(self._members):
            try:
                arrows = getattr(member, "arrows", None)
                if arrows:
                    for arrow in arrows:
                        if arrow not in all_arrows:
                            all_arrows.append(arrow)
            except Exception:
                pass

        # Сдвигаем карточки БЕЗ уведомления стрелок
        for member in list(self._members):
            try:
                member.blockSignals(True)

                pos = member.pos()
                member.setPos(pos.x() + dx, pos.y() + dy)

                member.blockSignals(False)
            except Exception:
                try:
                    member.blockSignals(False)
                except Exception:
                    pass

        # Теперь один раз обновляем ВСЕ стрелки одновременно
        for arrow in all_arrows:
            try:
                arrow.update_position()
            except Exception:
                pass

        try:
            from PySide6.QtCore import QPointF
            self._last_move_pos = QPointF(new_frame_pos)
        except Exception:
            pass

    def begin_move_with_members(self):
        self._moving_with_members = True

        try:
            from PySide6.QtCore import QPointF
            self._last_move_pos = QPointF(self.pos())
        except Exception:
            self._last_move_pos = None

    def end_move_with_members(self):
        self._moving_with_members = False
        self._last_move_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:

            # Resize Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’В·Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’В° Р В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р РЋРІвЂћСћР В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р РЋРЎв„ўР В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р В РІР‚В Р В Р’В Р Р†Р вЂљРЎв„ўР В Р’В Р В РІР‚в„–Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р РЋРЎС™Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В Р’В Р Р†Р вЂљР’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р РЋРІвЂћСћР В Р’В Р В РІР‚В Р В Р’В Р Р†Р вЂљРЎв„ўР В Р Р‹Р РЋРЎв„ў Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р РЋРЎвЂєР В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р В РІР‚В Р В Р’В Р Р†Р вЂљРЎв„ўР В Р Р‹Р Р†РІР‚С›РЎС›Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р РЋРЎвЂєР В Р вЂ Р В РІР‚С™Р вЂ™Р’ВР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’ВµР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’В»Р В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р вЂ™Р’В Р В Р’В Р Р†Р вЂљР’В°Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р вЂ™Р’В¦Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р РЋРЎвЂє.
            zone = resize_zone(self, event.pos())

            if zone is not None:
                start_resize(self, event.pos())
                event.accept()
                return

            # Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р РЋРІР‚СњР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’В±Р В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р В РІР‚В Р В Р’В Р Р†Р вЂљРЎв„ўР В Р вЂ Р Р†Р вЂљРЎвЂєР Р†Р вЂљРІР‚СљР В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р В РІР‚В Р В Р’В Р Р†Р вЂљРЎв„ўР В Р’В Р В РІР‚в„–Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р вЂ™Р’В¦Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р РЋРЎвЂєР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’Вµ Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р Р†Р вЂљРЎСљР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’ВµР В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р РЋРІвЂћСћР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’ВµР В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р В РІР‚В Р В Р’В Р Р†Р вЂљРЎв„ўР В Р Р‹Р Р†РІР‚С›РЎС›Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’В°Р В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р вЂ™Р’В Р В Р Р‹Р Р†Р вЂљРЎС™Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р РЋРЎС™Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р вЂ™Р’ВР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’В°Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р вЂ™Р’В¦Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р вЂ™Р’ВР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’Вµ Р В Р’В Р вЂ™Р’В Р В Р’В Р Р†Р вЂљР’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р РЋРІвЂћСћР В Р’В Р В РІР‚В Р В Р’В Р Р†Р вЂљРЎв„ўР В Р Р‹Р РЋРЎв„ў Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р вЂ™Р’В¦Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’В°Р В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р В РІР‚В Р В Р’В Р Р†Р вЂљРЎв„ўР В Р’В Р В РІР‚в„–Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р вЂ™Р’ВР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р вЂ™Р’В¦Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’В°Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’ВµР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р РЋРЎвЂєР В Р вЂ Р В РІР‚С™Р вЂ™Р’ВР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р вЂ™Р’ВР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’В¶Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’ВµР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р вЂ™Р’В¦Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р вЂ™Р’ВР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’Вµ Р В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р вЂ™Р’В Р В Р Р‹Р Р†Р вЂљРЎС™ Р В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р вЂ™Р’В Р В Р Р‹Р Р†Р вЂљРЎС™Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р РЋРЎвЂєР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р РЋРЎвЂєР В Р вЂ Р В РІР‚С™Р вЂ™Р’ВР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’ВµР В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р РЋРІвЂћСћР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’В¶Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р вЂ™Р’ВР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В РІР‚в„ўР вЂ™Р’ВР В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р В РІР‚В Р В Р’В Р Р†Р вЂљРЎв„ўР В Р вЂ Р Р†Р вЂљРЎвЂєР Р†Р вЂљРІР‚СљР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В РІР‚в„ўР вЂ™Р’В.
            self.begin_move_with_members()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, "resizing", False):
            apply_resize(self, event.pos())

            if self.overlay is not None:
                try:
                    self.overlay.update()
                except Exception:
                    pass

            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if getattr(self, "resizing", False):
            finish_resize(self)

            if self.overlay is not None:
                try:
                    self.overlay.update()
                except Exception:
                    pass

            event.accept()
            return

        super().mouseReleaseEvent(event)

        # Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В РІР‚В Р В Р’В Р Р†Р вЂљРЎв„ўР В Р вЂ Р В РІР‚С™Р РЋРЎС™Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’В°Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’ВµР В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р РЋРІвЂћСћР В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р В РІР‚В Р В Р вЂ Р В РІР‚С™Р РЋРІвЂћСћР В РІР‚в„ўР вЂ™Р’В¬Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’В°Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’ВµР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р РЋРЎвЂєР В Р вЂ Р В РІР‚С™Р вЂ™Р’ВР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р вЂ™Р’ВР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’В¶Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’ВµР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р вЂ™Р’В¦Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р вЂ™Р’ВР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’Вµ Р В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р вЂ™Р’В Р В Р Р‹Р Р†Р вЂљРЎС™ Р В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р вЂ™Р’В Р В Р Р‹Р Р†Р вЂљРЎС™Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р РЋРЎвЂєР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р РЋРЎвЂєР В Р вЂ Р В РІР‚С™Р вЂ™Р’ВР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’ВµР В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р вЂ™Р’В Р В Р вЂ Р В РІР‚С™Р РЋРІвЂћСћР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р Р†Р вЂљРІвЂћСћР В РІР‚в„ўР вЂ™Р’В¶Р В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В Р вЂ Р В РІР‚С™Р вЂ™Р’ВР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В РІР‚в„ўР вЂ™Р’ВР В Р’В Р вЂ™Р’В Р В Р’В Р В РІР‚в„–Р В Р’В Р В РІР‚В Р В Р’В Р Р†Р вЂљРЎв„ўР В Р вЂ Р Р†Р вЂљРЎвЂєР Р†Р вЂљРІР‚СљР В Р’В Р вЂ™Р’В Р В РІР‚в„ўР вЂ™Р’В Р В Р’В Р В Р вЂ№Р В РІР‚в„ўР вЂ™Р’В.
        self.end_move_with_members()

        try:
            from .frame_containment import update_all_memberships

            update_all_memberships(self.scene())

        except Exception as exc:
            print(f"[FRAME] update_all_memberships failed: {exc!r}")

    def _find_title_at(self, scene_pos):
        if self.title_item is None:
            return False

        try:
            local_pos = self.title_item.mapFromScene(scene_pos)

            if self.title_item.contains(local_pos):
                return True
        except Exception:
            pass

        return False

    def mouseDoubleClickEvent(self, event):
        if self._find_title_at(event.scenePos()):
            if self.title_item is not None:
                try:
                    self.title_item.set_editing_enabled(True)
                    self.title_item.setFocus()
                    event.accept()
                    return
                except Exception:
                    pass

        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu()

        rename_action = menu.addAction(LABEL_RENAME)
        color_action = menu.addAction(LABEL_CHANGE_COLOR)

        fill_menu = menu.addMenu(LABEL_FILL_MENU)
        fill_transparent_action = fill_menu.addAction(LABEL_FILL_TRANSPARENT)
        fill_white_action = fill_menu.addAction(LABEL_FILL_WHITE)
        fill_gray_action = fill_menu.addAction(LABEL_FILL_GRAY)
        fill_black_action = fill_menu.addAction(LABEL_FILL_BLACK)

        menu.addSeparator()
        autosize_action = menu.addAction(LABEL_AUTOSIZE)
        menu.addSeparator()
        lock_action = menu.addAction(LABEL_LOCK)
        menu.addSeparator()
        delete_action = menu.addAction(LABEL_DELETE)

        action = menu.exec(event.screenPos())

        if action == delete_action:
            self._delete_self()
        elif action == rename_action:
            self._rename_self()
        elif action == color_action:
            self._change_color()
        elif action == autosize_action:
            self._autosize_self()
        elif action == fill_transparent_action:
            self._set_fill_and_save("transparent")
        elif action == fill_white_action:
            self._set_fill_and_save("white")
        elif action == fill_gray_action:
            self._set_fill_and_save("gray")
        elif action == fill_black_action:
            self._set_fill_and_save("black")
        elif action == lock_action:
            self._set_locked_and_save(True)

    def _rename_self(self):
        scene = self.scene()

        if scene is None or not scene.views():
            return

        parent = scene.views()[0]

        new_title, ok = QInputDialog.getText(
            parent,
            LABEL_RENAME_DIALOG,
            LABEL_NEW_NAME,
            text=self.title,
        )

        if not ok:
            return

        new_title = new_title.strip()

        if not new_title:
            return

        self.title = new_title

        if self.title_item is not None:
            try:
                self.title_item.setPlainText(new_title)
            except Exception:
                pass

        self.update()

        try:
            canvas = getattr(parent, "canvas", None)

            if canvas is None:
                canvas = getattr(
                    getattr(parent, "main_window", None),
                    "canvas",
                    None,
                )

            if canvas is not None:
                canvas.save_board()

        except Exception:
            pass

    def _change_color(self):
        scene = self.scene()

        if scene is None or not scene.views():
            return

        parent = scene.views()[0]

        main_window = getattr(parent, "main_window", None)

        if main_window is None:
            return

        canvas = getattr(main_window, "canvas", None)

        if canvas is None:
            return

        show_palette = None

        try:
            from ..canvas import color as color_module

            for name in (
                "_show_color_palette",
                "show_palette",
                "_show_color_dialog",
            ):
                candidate = getattr(color_module, name, None)

                if callable(candidate):
                    show_palette = candidate
                    break

        except Exception:
            show_palette = None

        if show_palette is None:
            return

        try:
            show_palette(canvas, self)
        except TypeError:
            try:
                show_palette(self)
            except Exception:
                return
        except Exception:
            return

        try:
            canvas.save_board()
        except Exception:
            pass

    def _set_fill_and_save(self, name):
        self.set_frame_fill(name)

        scene = self.scene()

        if scene is None or not scene.views():
            return

        parent = scene.views()[0]

        try:
            canvas = getattr(parent, "canvas", None)

            if canvas is None:
                canvas = getattr(
                    getattr(parent, "main_window", None),
                    "canvas",
                    None,
                )

            if canvas is not None:
                canvas.save_board()

        except Exception:
            pass

    def _set_locked_and_save(self, locked):
        self.set_locked(locked)

        scene = self.scene()

        if scene is None or not scene.views():
            return

        parent = scene.views()[0]

        try:
            canvas = getattr(parent, "canvas", None)

            if canvas is None:
                canvas = getattr(
                    getattr(parent, "main_window", None),
                    "canvas",
                    None,
                )

            if canvas is not None:
                canvas.save_board()

        except Exception:
            pass

    def _autosize_self(self):
        ok = autosize_to_members(self)

        if self.title_item is not None:
            try:
                update_title_width(self.title_item, self.rect().width())
            except Exception:
                pass

        if self.overlay is not None:
            try:
                self.overlay.update()
            except Exception:
                pass

        scene = self.scene()

        if scene is None or not scene.views():
            return

        parent = scene.views()[0]

        if not ok:
            return

        try:
            canvas = getattr(parent, "canvas", None)

            if canvas is None:
                canvas = getattr(
                    getattr(parent, "main_window", None),
                    "canvas",
                    None,
                )

            if canvas is not None:
                canvas.save_board()

        except Exception:
            pass

    def _delete_self(self):
        scene = self.scene()

        if scene is None:
            return

        try:
            from .frame_containment import detach_all_members
            detach_all_members(self)
        except Exception:
            pass

        if self.overlay is not None:
            try:
                scene.removeItem(self.overlay)
            except Exception:
                pass

            self.overlay = None

        self._last_move_pos = None
        self._moving_with_members = False

        try:
            scene.removeItem(self)
        except Exception:
            pass


def add_frame(canvas, title=None):
    if canvas is None:
        return None

    if title is None:
        title = TITLE_DEFAULT

    x = 0.0
    y = 0.0

    try:
        center = canvas.mapToScene(canvas.viewport().rect().center())
        x = center.x() - FrameItem.DEFAULT_WIDTH / 2.0
        y = center.y() - FrameItem.DEFAULT_HEIGHT / 2.0
    except Exception:
        pass

    frame = FrameItem(x=x, y=y, title=title)

    try:
        canvas.scene.addItem(frame)
    except Exception:
        return None

    try:
        from .frame_containment import update_all_memberships

        update_all_memberships(canvas.scene)

    except Exception as exc:
        print(f"[ADD_FRAME] update_all_memberships failed: {exc!r}")

    try:
        frame.setSelected(True)
    except Exception:
        pass

    try:
        canvas.save_board()
    except Exception:
        pass

    try:
        canvas.main_window.update_status(LABEL_FRAME_ADDED)
    except Exception:
        pass

    return frame
