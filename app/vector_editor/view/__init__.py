"""
View-слой векторного редактора. Qt-зависимый.
"""

from .canvas import VectorCanvas
from .scene import VectorScene
from .asset_browser import AssetBrowser
from .save_asset_dialog import SaveAssetDialog
from .semantic_group_dialog import SemanticGroupDialog
from .semantic_groups_panel import SemanticGroupsPanel
from .parameter_dialog import ParameterDialog
from .parameters_panel import ParametersPanel
from .stretch_dialog import StretchDialog
from .reference_properties_dialog import ReferencePropertiesDialog
from .items.contour_item import ContourItem
from .items.node_item import NodeItem
from .items.drawing_preview import DrawingPreviewItem
from .items.reference_item import ReferenceImageItem

__all__ = [
    "VectorCanvas",
    "VectorScene",
    "AssetBrowser",
    "SaveAssetDialog",
    "SemanticGroupDialog",
    "SemanticGroupsPanel",
    "ParameterDialog",
    "ParametersPanel",
    "StretchDialog",
    "ReferencePropertiesDialog",
    "ContourItem",
    "NodeItem",
    "DrawingPreviewItem",
    "ReferenceImageItem",
]
