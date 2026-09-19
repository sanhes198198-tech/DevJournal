"""
Модель векторного редактора. Чистые данные, без Qt.
"""

from .contour import VectorContour
from .geometry import dist_point_to_segment
from .operations import extrude_face
from .asset import (
    Asset,
    ASSET_TYPES,
    ASSET_TYPE_IDS,
)
from .semantic_group import SemanticGroup

__all__ = [
    "VectorContour",
    "dist_point_to_segment",
    "extrude_face",
    "Asset",
    "ASSET_TYPES",
    "ASSET_TYPE_IDS",
    "SemanticGroup",
]
