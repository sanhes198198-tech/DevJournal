"""
View-слой векторного редактора. Qt-зависимый.
"""

from .canvas import VectorCanvas
from .scene import VectorScene
from .asset_browser import AssetBrowser
from .save_asset_dialog import SaveAssetDialog
from .semantic_group_dialog import SemanticGroupDialog
from .semantic_groups_panel import SemanticGroupsPanel
from .items.contour_item import ContourItem
from .items.node_item import NodeItem
from .items.drawing_preview import DrawingPreviewItem

__all__ = [
    "VectorCanvas",
    "VectorScene",
    "AssetBrowser",
    "SaveAssetDialog",
    "SemanticGroupDialog",
    "SemanticGroupsPanel",
    "ContourItem",
    "NodeItem",
    "DrawingPreviewItem",
]
