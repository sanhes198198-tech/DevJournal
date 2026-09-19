"""
IO для векторного редактора.
"""

from .storage import (
    ASSETS_DIR,
    ensure_assets_dir,
    save_asset,
    load_asset,
    list_assets,
    delete_asset,
    asset_exists,
    StorageError,
)
from .reference import (
    save_reference_image_png,
    delete_reference_image_file,
    get_reference_image_path,
)

__all__ = [
    "ASSETS_DIR",
    "ensure_assets_dir",
    "save_asset",
    "load_asset",
    "list_assets",
    "delete_asset",
    "asset_exists",
    "StorageError",
    "save_reference_image_png",
    "delete_reference_image_file",
    "get_reference_image_path",
]
