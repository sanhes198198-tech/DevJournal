"""
View-слой векторного редактора. Qt-зависимый.
"""

from .canvas import VectorCanvas
from .scene import VectorScene
from .save_asset_dialog import SaveAssetDialog
from .items.contour_item import ContourItem
from .items.node_item import NodeItem
from .items.drawing_preview import DrawingPreviewItem

__all__ = [
    "VectorCanvas",
    "VectorScene",
    "SaveAssetDialog",
    "ContourItem",
    "NodeItem",
    "DrawingPreviewItem",
]
