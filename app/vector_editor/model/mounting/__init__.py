"""
Mounting - точки крепления для Asset.

Не путать с SemanticGroup + auto_rule - это legacy.
Mounting - новая модель (MountPoint -> MountLocation).
"""

from .mount_role import MountRole, parse_role, role_to_str
from .mount_point import MountPoint, Distribution, MountLocation
from .attachment import Attachment
from .migration import (
    migrate_asset,
    apply_migration,
)

__all__ = [
    "MountRole",
    "parse_role",
    "role_to_str",
    "MountPoint",
    "Distribution",
    "MountLocation",
    "Attachment",
    "migrate_asset",
    "apply_migration",
]
