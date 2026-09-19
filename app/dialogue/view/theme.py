"""
Цветовая палитра Dialogue Editor.

Только константы. Никакой логики рисования.
Flat / Thin / Precise.
"""

BG_SCENE       = "#111214"
BG_PANEL       = "#17191C"
BG_TOOLBAR     = "#17191C"
BG_CARD        = "#202328"
BG_CARD_HOVER  = "#292D32"
BG_INPUT       = "#1A1C20"
BG_HOVER       = "#292D32"

BORDER         = "#2A2D33"
BORDER_FOCUS   = "#4A90E2"
BORDER_SELECT  = "#4A90E2"

TEXT_PRIMARY   = "#E5E5E5"
TEXT_SECONDARY = "#858B93"
TEXT_DIM       = "#5A5F68"

ACCENT_START   = "#7ED321"
ACCENT_REPLY   = "#4A90E2"
ACCENT_CHOICE  = "#F5A623"
ACCENT_END     = "#B85C63"

CONN_NORMAL    = "#3A3F48"
CONN_HOVER     = "#4A90E2"
CONN_SELECT    = "#4A90E2"

ACCENT_BY_TYPE = {
    "start":  ACCENT_START,
    "reply":  ACCENT_REPLY,
    "choice": ACCENT_CHOICE,
    "end":    ACCENT_END,
}


def accent_for(node_type):
    return ACCENT_BY_TYPE.get(node_type, TEXT_SECONDARY)