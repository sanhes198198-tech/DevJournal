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

__all__ = [
    "ASSETS_DIR",
    "ensure_assets_dir",
    "save_asset",
    "load_asset",
    "list_assets",
    "delete_asset",
    "asset_exists",
    "StorageError",
]
