"""
Модель архитектуры — чистые данные, без Qt.
"""

from .architecture import ArchitectureModel, SCHEMA_VERSION
from .element import ArchElement
from .room import Room
from .asset_instance import AssetInstance
from .registry import (
    ELEMENT_TYPES,
    UnknownElementType,
    element_from_dict,
)

__all__ = [
    "ArchitectureModel",
    "SCHEMA_VERSION",
    "ArchElement",
    "Room",
    "AssetInstance",
    "ELEMENT_TYPES",
    "UnknownElementType",
    "element_from_dict",
]
