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
from .parameter import (
    Parameter,
    ParameterTarget,
    compute_delta_for_parameter,
    compute_combined_delta,
    apply_delta_to_points,
)
from .reference_image import ReferenceImage
from .component import Component
from .visibility_rule import VisibilityRule
from .analysis import (
    AUTO_GROUP_TYPES,
    generate_auto_group,
    find_horizontal_edge_nodes,
    find_vertical_edge_nodes,
    find_convex_nodes,
    find_concave_nodes,
)

__all__ = [
    "VectorContour",
    "dist_point_to_segment",
    "extrude_face",
    "Asset",
    "ASSET_TYPES",
    "ASSET_TYPE_IDS",
    "SemanticGroup",
    "Parameter",
    "ParameterTarget",
    "compute_delta_for_parameter",
    "compute_combined_delta",
    "apply_delta_to_points",
    "ReferenceImage",
    "Component",
    "VisibilityRule",
    "AUTO_GROUP_TYPES",
    "generate_auto_group",
    "find_horizontal_edge_nodes",
    "find_vertical_edge_nodes",
    "find_convex_nodes",
    "find_concave_nodes",
]
