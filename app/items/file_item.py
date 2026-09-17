import os
import uuid

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsTextItem,
    QMenu,
)


class FileItem(QGraphicsItem):

    ICON_WIDTH = 100
    ICON_HEIGHT = 125

    WIDTH = 160
    HEIGHT = 165

    def __init__(
        self,
        file_path="",
        file_name="",
    ):
        super().__init__()

        self.file_path = file_path

        self.file_name = (
            file_name
            or os.path.basename(file_path)
        )

        self.file_id = str(uuid.uuid4())

        self.runtime_file_path = file_path

        # Р СџРЎР‚Р С‘Р Р†РЎРЏР В·Р С”Р В° Р С” РЎР‚Р В°Р СР С”Р Вµ (РЎС“РЎРѓРЎвЂљР В°Р Р…Р В°Р Р†Р В»Р С‘Р Р†Р В°Р ВµРЎвЂљРЎРѓРЎРЏ frame_containment)
        self._frame = None

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        )

        # Р РЋРЎвЂљРЎР‚Р ВµР В»Р С”Р С‘, Р С—РЎР‚Р С‘Р Р†РЎРЏР В·Р В°Р Р…Р Р…РЎвЂ№Р Вµ Р С” РЎРЊРЎвЂљР С•Р СРЎС“ РЎРЊР В»Р ВµР СР ВµР Р…РЎвЂљРЎС“
        self.arrows = []

        # =================================================
        # FILE NAME
        # =================================================

        self.name_item = QGraphicsTextItem(
            self.file_name,
            self,
        )

        self.name_item.setDefaultTextColor(
            QColor("#202124")
        )

        self.name_item.setFont(
            QFont(
                "Segoe UI",
                9,
            )
        )

        self.name_item.setTextWidth(
            self.WIDTH
        )

        self.name_item.setPos(
            0,
            self.ICON_HEIGHT + 10,
        )

        # Р СћР ВµР С”РЎРѓРЎвЂљ Р Р…Р Вµ Р Т‘Р С•Р В»Р В¶Р ВµР Р… Р СР ВµРЎв‚¬Р В°РЎвЂљРЎРЉ Р С—Р ВµРЎР‚Р ВµР СР ВµРЎвЂ°Р ВµР Р…Р С‘РЎР‹ РЎвЂћР В°Р в„–Р В»Р В°
        self.name_item.setAcceptedMouseButtons(
            Qt.MouseButton.NoButton
        )

    # =====================================================
    # ARROWS
    # =====================================================

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

    # =====================================================
    # CONNECTION POINT
    # =====================================================

    def has_connection_point(
        self,
    ):
        return True

    def connection_point(
        self,
    ):
        return QPointF(
            self.WIDTH / 2,
            0,
        )

    # =====================================================
    # BOUNDING RECT
    # =====================================================

    def boundingRect(self):

        return QRectF(
            0,
            0,
            self.WIDTH,
            self.HEIGHT,
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

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        # -------------------------------------------------
        # DOCUMENT
        # -------------------------------------------------

        left = (
            self.WIDTH - self.ICON_WIDTH
        ) / 2

        top = 0

        width = self.ICON_WIDTH
        height = self.ICON_HEIGHT

        fold = 22

        document = QPainterPath()

        document.moveTo(
            left,
            top,
        )

        document.lineTo(
            left + width - fold,
            top,
        )

        document.lineTo(
            left + width,
            top + fold,
        )

        document.lineTo(
            left + width,
            top + height,
        )

        document.lineTo(
            left,
            top + height,
        )

        document.closeSubpath()

        # Р вЂР ВµР В»РЎвЂ№Р в„– Р В»Р С‘РЎРѓРЎвЂљ
        painter.setBrush(
            QColor("#FFFFFF")
        )

        painter.setPen(
            QPen(
                QColor("#BFC3C7"),
                1.2,
            )
        )

        painter.drawPath(
            document
        )

        # -------------------------------------------------
        # FOLDED CORNER
        # -------------------------------------------------

        fold_path = QPainterPath()

        fold_path.moveTo(
            left + width - fold,
            top,
        )

        fold_path.lineTo(
            left + width - fold,
            top + fold,
        )

        fold_path.lineTo(
            left + width,
            top + fold,
        )

        fold_path.closeSubpath()

        painter.setBrush(
            QColor("#E5E7EA")
        )

        painter.setPen(
            QPen(
                QColor("#BFC3C7"),
                1,
            )
        )

        painter.drawPath(
            fold_path
        )

        # -------------------------------------------------
        # DOCUMENT LINES
        # -------------------------------------------------

        line_left = left + 15
        line_right = left + width - 15

        lines = [
            top + 42,
            top + 56,
            top + 70,
            top + 84,
        ]

        painter.setPen(
            QPen(
                QColor("#C7CBD0"),
                2,
            )
        )

        for y in lines:

            painter.drawLine(
                QPointF(
                    line_left,
                    y,
                ),
                QPointF(
                    line_right,
                    y,
                ),
            )

        # -------------------------------------------------
        # FILE TYPE BADGE
        # -------------------------------------------------

        extension = os.path.splitext(
            self.file_name
        )[1].lower()

        if extension == ".docx":
            badge_text = "W"
        elif extension == ".doc":
            badge_text = "W"
        elif extension:
            badge_text = extension[1:].upper()
        else:
            badge_text = "FILE"

        badge_width = 34
        badge_height = 24

        badge_x = (
            left
            + width
            - badge_width
            - 10
        )

        badge_y = (
            top
            + height
            - badge_height
            - 10
        )

        painter.setBrush(
            QColor("#2B579A")
        )

        painter.setPen(
            Qt.PenStyle.NoPen
        )

        painter.drawRoundedRect(
            QRectF(
                badge_x,
                badge_y,
                badge_width,
                badge_height,
            ),
            4,
            4,
        )

        # РўРµРєСЃС‚ РІРЅСѓС‚СЂРё Р·РЅР°С‡РєР°
        painter.setPen(
            QColor("#FFFFFF")
        )

        painter.setFont(
            QFont(
                "Segoe UI",
                7,
                QFont.Weight.Bold,
            )
        )

        painter.drawText(
            QRectF(
                badge_x,
                badge_y,
                badge_width,
                badge_height,
            ),
            Qt.AlignmentFlag.AlignCenter,
            badge_text,
        )

        # -------------------------------------------------
        # SELECTION
        # -------------------------------------------------

        if self.isSelected():

            painter.setBrush(
                Qt.BrushStyle.NoBrush
            )

            painter.setPen(
                QPen(
                    QColor("#4285F4"),
                    1.5,
                    Qt.PenStyle.DashLine,
                )
            )

            painter.drawRect(
                QRectF(
                    left - 4,
                    top - 4,
                    width + 8,
                    height + 8,
                )
            )

    # =====================================================
    # OPEN FILE
    # =====================================================

    def open_file(self):

        path = getattr(
            self,
            "runtime_file_path",
            self.file_path,
        )

        if not path:
            return

        path = os.path.abspath(
            path
        )

        if not os.path.exists(
            path
        ):
            return

        try:

            os.startfile(
                path
            )

        except Exception:

            os.system(
                f'start "" "{path}"'
            )

    # =====================================================
    # DOUBLE CLICK
    # =====================================================

    def mouseDoubleClickEvent(
        self,
        event,
    ):

        if (
            event.button()
            == Qt.MouseButton.LeftButton
        ):

            self.open_file()

            event.accept()

            return

        super().mouseDoubleClickEvent(
            event
        )

    # =====================================================
    # MOUSE RELEASE
    # =====================================================

    def mouseReleaseEvent(
        self,
        event,
    ):

        super().mouseReleaseEvent(
            event
        )

        # =================================================
        # FRAME MEMBERSHIP
        # =================================================

        if event.button() == Qt.MouseButton.LeftButton:

            try:
                from ..canvas.frame_containment import (
                    update_item_membership,
                )

                update_item_membership(
                    self,
                    self.scene(),
                )

            except Exception as exc:
                print(
                    f"[FILE] membership update failed: {exc!r}"
                )

    # =====================================================
    # CONTEXT MENU
    # =====================================================

    def contextMenuEvent(
        self,
        event,
    ):

        menu = QMenu()

        open_action = menu.addAction(
            "РћС‚РєСЂС‹С‚СЊ"
        )

        delete_action = menu.addAction(
            "РЈРґР°Р»РёС‚СЊ"
        )

        action = menu.exec(
            event.screenPos()
        )

        if action == open_action:

            self.open_file()

        elif action == delete_action:

            if self.scene():

                views = self.scene().views()

                if views:

                    view = views[0]

                    if hasattr(
                        view,
                        "delete_item",
                    ):

                        view.delete_item(
                            self
                        )

        event.accept()