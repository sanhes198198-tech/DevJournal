"""
Frame overlay - draws frame border + resize handles above cards.

The real FrameItem stays at low z (-500), under cards. This overlay
sits at high z (600) so the frame's border and resize handles are
always visible and grabbable.

Mouse handling:
- the overlay only accepts mouse in the resize-handle zones;
- everywhere else mouse passes through to underlying items.
"""

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QPen,
    QBrush,
    QColor,
    QPainterPath,
)
from PySide6.QtWidgets import QGraphicsItem


# ============================================================
# CONFIG
# ============================================================

OVERLAY_Z = 600.0

HANDLE_SIZE = 10.0       # СЂР°Р·РјРµСЂ РєРІР°РґСЂР°С‚РЅРѕР№ СЂСѓС‡РєРё (РІРёР·СѓР°Р»СЊРЅРѕ)
HANDLE_HIT_MARGIN = 6.0  # СЂР°СЃС€РёСЂРµРЅРёРµ Р·РѕРЅС‹ Р·Р°С…РІР°С‚Р° РІРѕРєСЂСѓРі СЂСѓС‡РєРё

BORDER_WIDTH_NORMAL = 1.5
BORDER_WIDTH_SELECTED = 2.0

BORDER_COLOR_NORMAL = QColor("#B0B0B0")
BORDER_COLOR_SELECTED = QColor("#4F7CFF")

HANDLE_FILL = QColor("#FFFFFF")
HANDLE_BORDER = QColor("#4F7CFF")


# ============================================================
# HELPERS
# ============================================================

def _handle_positions(rect):
    """
    Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє (name, QPointF) РґР»СЏ 8 СЂСѓС‡РµРє.
    """

    left = rect.left()
    right = rect.right()
    top = rect.top()
    bottom = rect.bottom()

    cx = (left + right) / 2.0
    cy = (top + bottom) / 2.0

    return [
        ("tl", QPointF(left, top)),
        ("tr", QPointF(right, top)),
        ("bl", QPointF(left, bottom)),
        ("br", QPointF(right, bottom)),
        ("t", QPointF(cx, top)),
        ("b", QPointF(cx, bottom)),
        ("l", QPointF(left, cy)),
        ("r", QPointF(right, cy)),
    ]


def _cursor_for_handle(name):
    """
    Р’РѕР·РІСЂР°С‰Р°РµС‚ Qt.CursorShape РїРѕ РёРјРµРЅРё СЂСѓС‡РєРё.
    """

    mapping = {
        "tl": Qt.CursorShape.SizeFDiagCursor,
        "br": Qt.CursorShape.SizeFDiagCursor,
        "tr": Qt.CursorShape.SizeBDiagCursor,
        "bl": Qt.CursorShape.SizeBDiagCursor,
        "t": Qt.CursorShape.SizeVerCursor,
        "b": Qt.CursorShape.SizeVerCursor,
        "l": Qt.CursorShape.SizeHorCursor,
        "r": Qt.CursorShape.SizeHorCursor,
    }

    return mapping.get(name, Qt.CursorShape.ArrowCursor)


# ============================================================
# OVERLAY ITEM
# ============================================================

class FrameOverlay(QGraphicsItem):
    """
    Overlay that draws frame border + resize handles above cards.

    It does NOT store its own geometry - it always reads from
    the underlying FrameItem.
    """

    def __init__(self, frame):
        super().__init__()

        self.frame = frame

        self._hover_handle = None

        self.setZValue(OVERLAY_Z)

        # Selectable handles only (we click them to resize).
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
            False,
        )

        self.setAcceptHoverEvents(True)

        # Mouse is accepted manually in shape()/mousePressEvent,
        # but only in handle zones.
        self.setAcceptedMouseButtons(
            Qt.MouseButton.LeftButton
        )

    # --------------------------------------------------------
    # GEOMETRY (always synced with frame)
    # --------------------------------------------------------

    def boundingRect(self):
        """
        РџРѕР»РЅС‹Р№ bounding rect СЂР°РјРєРё РІ Р»РѕРєР°Р»СЊРЅС‹С… РєРѕРѕСЂРґРёРЅР°С‚Р°С… overlay.

        Overlay РїРѕР·РёС†РёРѕРЅРёСЂСѓРµС‚СЃСЏ РІ scene coords 1:1 СЃ СЂР°РјРєРѕР№:
        РµРіРѕ pos() = frame.pos(), РЅРѕ РјС‹ РќР• РёСЃРїРѕР»СЊР·СѓРµРј mapToScene
        РґР»СЏ СЂСѓС‡РµРє - СЂР°Р±РѕС‚Р°РµРј РІ scene-РєРѕРѕСЂРґРёРЅР°С‚Р°С… РЅР°РїСЂСЏРјСѓСЋ.

        РџРѕСЌС‚РѕРјСѓ boundingRect = frame.rect() + Р·Р°РїР°СЃ РЅР° СЂСѓС‡РєРё.
        """

        if self.frame is None:
            return QRectF()

        try:
            rect = self.frame.rect()
        except Exception:
            return QRectF()

        margin = HANDLE_SIZE + HANDLE_HIT_MARGIN + 2.0

        return rect.adjusted(
            -margin,
            -margin,
            margin,
            margin,
        )

    # --------------------------------------------------------
    # PAINT
    # --------------------------------------------------------

    def paint(self, painter, option, widget=None):
        if self.frame is None:
            return

        try:
            rect = self.frame.rect()
        except Exception:
            return

        selected = False

        try:
            selected = self.frame.isSelected()
        except Exception:
            pass

        # Border
        if selected:
            pen = QPen(
                BORDER_COLOR_SELECTED,
                BORDER_WIDTH_SELECTED,
                Qt.PenStyle.DashLine,
            )
        else:
            pen = QPen(
                BORDER_COLOR_NORMAL,
                BORDER_WIDTH_NORMAL,
                Qt.PenStyle.DashLine,
            )

        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.drawRect(rect)

        # Handles (only when selected)
        if selected:

            painter.setPen(
                QPen(HANDLE_BORDER, 1.2)
            )
            painter.setBrush(
                QBrush(HANDLE_FILL)
            )

            half = HANDLE_SIZE / 2.0

            for name, pos in _handle_positions(rect):

                handle_rect = QRectF(
                    pos.x() - half,
                    pos.y() - half,
                    HANDLE_SIZE,
                    HANDLE_SIZE,
                )

                painter.drawRect(handle_rect)

    # --------------------------------------------------------
    # SHAPE (hit test)
    # --------------------------------------------------------

    def shape(self):
        """
        Р’РѕР·РІСЂР°С‰Р°РµС‚ С„РѕСЂРјСѓ, РїРѕ РєРѕС‚РѕСЂРѕР№ overlay РїСЂРёРЅРёРјР°РµС‚ РјС‹С€СЊ.

        РўРѕР»СЊРєРѕ Р·РѕРЅС‹ СЂСѓС‡РµРє + С‚РѕРЅРєР°СЏ РіСЂР°РЅРёС†Р° РІ СЂРµР¶РёРјРµ РІС‹РґРµР»РµРЅРёСЏ.
        Р’ РѕСЃС‚Р°Р»СЊРЅС‹С… РјРµСЃС‚Р°С… С„РѕСЂРјР° РїСѓСЃС‚Р°СЏ - РєР»РёРє РїСЂРѕС…РѕРґРёС‚ РІРЅРёР·.
        """

        path = QPainterPath()

        if self.frame is None:
            return path

        try:
            rect = self.frame.rect()
        except Exception:
            return path

        try:
            selected = self.frame.isSelected()
        except Exception:
            selected = False

        if not selected:
            # РџРѕРєР° РЅРµ РІС‹РґРµР»РµРЅРѕ - РЅРµ РїРµСЂРµС…РІР°С‚С‹РІР°РµРј РјС‹С€СЊ РІРѕРѕР±С‰Рµ.
            return path

        # --- Handle zones ---

        half = (HANDLE_SIZE / 2.0) + HANDLE_HIT_MARGIN

        for name, pos in _handle_positions(rect):

            zone = QRectF(
                pos.x() - half,
                pos.y() - half,
                half * 2.0,
                half * 2.0,
            )

            path.addRect(zone)

        # --- Thin border zone for drag ---
        # (С‡С‚РѕР±С‹ РјРѕР¶РЅРѕ Р±С‹Р»Рѕ С‚СЏРЅСѓС‚СЊ СЂР°РјРєСѓ Р·Р° РіСЂР°РЅРёС†Сѓ, РґР°Р¶Рµ РµСЃР»Рё
        #  РѕРЅР° РїРѕРґ РєР°СЂС‚РѕС‡РєРѕР№)

        border_thickness = 6.0

        # top
        path.addRect(
            QRectF(
                rect.left() - border_thickness,
                rect.top() - border_thickness,
                rect.width() + border_thickness * 2,
                border_thickness * 2,
            )
        )

        # bottom
        path.addRect(
            QRectF(
                rect.left() - border_thickness,
                rect.bottom() - border_thickness,
                rect.width() + border_thickness * 2,
                border_thickness * 2,
            )
        )

        # left
        path.addRect(
            QRectF(
                rect.left() - border_thickness,
                rect.top() - border_thickness,
                border_thickness * 2,
                rect.height() + border_thickness * 2,
            )
        )

        # right
        path.addRect(
            QRectF(
                rect.right() - border_thickness,
                rect.top() - border_thickness,
                border_thickness * 2,
                rect.height() + border_thickness * 2,
            )
        )

        return path

    # --------------------------------------------------------
    # HOVER
    # --------------------------------------------------------

    def hoverMoveEvent(self, event):
        """
        РњРµРЅСЏРµС‚ РєСѓСЂСЃРѕСЂ, РµСЃР»Рё РјС‹С€СЊ РЅР°Рґ СЂСѓС‡РєРѕР№.
        """

        if self.frame is None:
            return

        handle = self._handle_at(event.pos())

        self._hover_handle = handle

        if handle:
            try:
                self.setCursor(
                    _cursor_for_handle(handle)
                )
            except Exception:
                pass
        else:
            try:
                self.setCursor(
                    Qt.CursorShape.SizeAllCursor
                )
            except Exception:
                pass

        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self._hover_handle = None

        try:
            self.unsetCursor()
        except Exception:
            pass

        super().hoverLeaveEvent(event)

    # --------------------------------------------------------
    # MOUSE
    # --------------------------------------------------------

    def _handle_at(self, local_pos):
        """
        Р’РѕР·РІСЂР°С‰Р°РµС‚ РёРјСЏ СЂСѓС‡РєРё РїРѕРґ local_pos РёР»Рё None.
        """

        if self.frame is None:
            return None

        try:
            rect = self.frame.rect()
        except Exception:
            return None

        half = (HANDLE_SIZE / 2.0) + HANDLE_HIT_MARGIN

        for name, pos in _handle_positions(rect):

            zone = QRectF(
                pos.x() - half,
                pos.y() - half,
                half * 2.0,
                half * 2.0,
            )

            if zone.contains(local_pos):
                return name

        return None

    def mousePressEvent(self, event):
        """
        РџРµСЂРµРґР°С‘Рј РЅР°Р¶Р°С‚РёРµ РІ FrameItem.start_resize.

        Overlay Рё frame РёРјРµСЋС‚ РѕРґРёРЅР°РєРѕРІСѓСЋ Р»РѕРєР°Р»СЊРЅСѓСЋ СЃРёСЃС‚РµРјСѓ
        РєРѕРѕСЂРґРёРЅР°С‚ (pos СЃРѕРІРїР°РґР°РµС‚), РїРѕСЌС‚РѕРјСѓ event.pos()
        РїРµСЂРµРґР°С‘С‚СЃСЏ 1:1.
        """

        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return

        if self.frame is None:
            event.ignore()
            return

        try:
            from .frame_resize import resize_zone, start_resize

            # Р—Р°СЃС‚Р°РІР»СЏРµРј СЂР°РјРєСѓ РІС‹РґРµР»РёС‚СЊСЃСЏ.
            try:
                self.frame.setSelected(True)
            except Exception:
                pass

            # РЎС‚Р°СЂС‚СѓРµРј resize РЅР°РїСЂСЏРјСѓСЋ.
            start_resize(self.frame, event.pos())
            event.accept()

        except Exception:
            event.ignore()

    def mouseMoveEvent(self, event):
        """
        РџРµСЂРµРґР°С‘Рј РґРІРёР¶РµРЅРёРµ РІ apply_resize.
        """

        if self.frame is None:
            event.ignore()
            return

        try:
            from .frame_resize import apply_resize

            apply_resize(self.frame, event.pos())
            event.accept()

        except Exception:
            event.ignore()

    def mouseReleaseEvent(self, event):
        """
        Р—Р°РІРµСЂС€Р°РµРј resize.
        """

        if self.frame is None:
            event.ignore()
            return

        try:
            from .frame_resize import finish_resize

            finish_resize(self.frame)

            # РћР±РЅРѕРІР»СЏРµРј containment.
            try:
                from .frame_containment import update_all_memberships

                update_all_memberships(self.frame.scene())
            except Exception:
                pass

            event.accept()

        except Exception:
            event.ignore()


# ============================================================
# FACTORY
# ============================================================

def create_frame_overlay(frame):
    """
    РЎРѕР·РґР°С‘С‚ Рё РґРѕР±Р°РІР»СЏРµС‚ overlay РЅР° СЃС†РµРЅСѓ.
    Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРѕР·РґР°РЅРЅС‹Р№ overlay РёР»Рё None.
    """

    if frame is None:
        return None

    scene = None

    try:
        scene = frame.scene()
    except Exception:
        scene = None

    if scene is None:
        return None

    try:
        overlay = FrameOverlay(frame)

        # Overlay РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РЅР° С‚РѕР№ Р¶Рµ РїРѕР·РёС†РёРё, С‡С‚Рѕ Рё СЂР°РјРєР°.
        # Р›РѕРєР°Р»СЊРЅР°СЏ СЃРёСЃС‚РµРјР°: overlay.pos() = frame.pos().
        # Р СѓС‡РєРё Сѓ РЅР°СЃ РІ scene-coords, РЅРѕ overlay "Р¶РёРІС‘С‚" РІ С‚РµС… Р¶Рµ
        # РєРѕРѕСЂРґРёРЅР°С‚Р°С…, С‡С‚Рѕ Рё frame (СЃРјРµС‰РµРЅРёРµ = frame.pos()).
        overlay.setPos(frame.pos())

        scene.addItem(overlay)

        return overlay

    except Exception:
        return None