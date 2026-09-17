"""
Frame title as editable text.

Uses the same EditableText as cards:
- double click to start editing
- font / size / bold / italic via the toolbar
"""

from ..cards.base.editable_text import EditableText


# ============================================================
# FACTORY
# ============================================================

def create_frame_title(text, parent_frame):
    """
    Creates an EditableText for the frame title.

    parent_frame вЂ” FrameItem the title belongs to.
    """

    if parent_frame is None:
        return None

    try:
        title_item = EditableText(
            text or "",
            parent_frame,
        )
    except Exception:
        return None

    # Position inside the frame: top-left with small padding.
    try:
        title_item.setPos(
            8,
            4,
        )
    except Exception:
        pass

    # Width вЂ” frame width minus padding.
    try:
        rect = parent_frame.rect()

        title_item.setTextWidth(
            max(
                50,
                rect.width() - 16,
            )
        )
    except Exception:
        pass

    # By default editing is disabled.
    try:
        title_item.set_editing_enabled(
            False
        )
    except Exception:
        pass

    return title_item


# ============================================================
# UPDATE WIDTH
# ============================================================

def update_title_width(title_item, frame_width):
    """
    Updates the title width when the frame is resized.
    """

    if title_item is None:
        return

    try:
        title_item.setTextWidth(
            max(
                50,
                frame_width - 16,
            )
        )
    except Exception:
        pass


# ============================================================
# HTML / TEXT HELPERS
# ============================================================

def get_title_html(title_item):
    """
    Returns the title HTML for board.json.
    """

    if title_item is None:
        return ""

    try:
        return title_item.toHtml()
    except Exception:
        return ""


def get_title_text(title_item):
    """
    Returns the title plain text.
    """

    if title_item is None:
        return ""

    try:
        return title_item.toPlainText()
    except Exception:
        return ""


def set_title_html(title_item, html):
    """
    Restores the title from HTML.
    """

    if title_item is None:
        return

    if not html:
        return

    try:
        title_item.setHtml(html)
    except Exception:
        pass


# ============================================================
# SYNC WITH FRAME.title
# ============================================================

def connect_title_changes(frame):
    """
    Connects the text-changed signal so that frame.title
    always stays in sync with the EditableText.

    This is needed because frame_persistence still reads
    frame.title as the plain-text fallback.
    """

    if frame is None:
        return

    title_item = getattr(frame, "title_item", None)

    if title_item is None:
        return

    try:
        document = title_item.document()
    except Exception:
        return

    def on_changed():

        try:
            frame.title = title_item.toPlainText()
        except Exception:
            pass

    try:
        document.contentsChanged.connect(on_changed)
    except Exception:
        pass