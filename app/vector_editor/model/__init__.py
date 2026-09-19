"""
Модель векторного редактора. Чистые данные, без Qt.
"""

from .contour import VectorContour
from .geometry import dist_point_to_segment

__all__ = ["VectorContour", "dist_point_to_segment"]
