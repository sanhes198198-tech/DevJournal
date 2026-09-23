"""
Reference Image — сохранение / удаление файлов картинки-подложки.

Картинка всегда PNG, имя файла: <asset_id>_ref.png в ASSETS_DIR.
Имя (не полный путь) кладётся в ReferenceImage.filename.
"""

from __future__ import annotations

import os

from pathlib import Path

from .storage import ASSETS_DIR, StorageError


def save_reference_image_png(asset_id: str, png_bytes: bytes) -> str:
    """Сохранить PNG-байты как <asset_id>_ref.png в assets/.

    Возвращает имя файла (не полный путь).
    """
    if not asset_id:
        raise StorageError("asset_id пустой")
    if not png_bytes:
        raise StorageError("png_bytes пустой")

    filename = f"{asset_id}_ref.png"
    path = ASSETS_DIR / filename

    # V19: атомарная запись — tmp → replace.
    # Так можно перезаписать файл, даже если он открыт в Photos/просмотрщике.
    tmp_path = path.with_suffix(".png.tmp")

    try:
        tmp_path.write_bytes(png_bytes)
    except OSError as e:
        raise StorageError(
            f"Не удалось записать временный файл: {e}"
        )

    try:
        os.replace(tmp_path, path)
    except OSError as e:
        # чистим tmp
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise StorageError(
            "Не удалось заменить картинку. "
            "Закрой её в другой программе (Photos, просмотрщик) "
            f"и попробуй снова. Детали: {e}"
        )

    return filename


def delete_reference_image_file(filename: str) -> bool:
    """Удалить файл картинки. Не падает, если файла нет.

    Возвращает True, если файл реально удалён.
    """
    if not filename:
        return False
    path = ASSETS_DIR / filename
    if not path.exists():
        return False
    try:
        path.unlink()
        return True
    except OSError:
        return False


def get_reference_image_path(filename: str) -> Path:
    """Полный путь к файлу картинки (без проверки существования)."""
    return ASSETS_DIR / filename
