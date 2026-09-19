"""
Геометрические хелперы. Чистая математика, без Qt.
"""

from __future__ import annotations

import math


def dist_point_to_segment(
    px: float, py: float,
    x1: float, y1: float,
    x2: float, y2: float,
) -> tuple[float, float]:
    """Расстояние от точки P до отрезка AB и параметр t (0..1).

    t=0 → проекция в A, t=1 → в B.
    """
    dx = x2 - x1
    dy = y2 - y1

    if dx == 0.0 and dy == 0.0:
        return (math.hypot(px - x1, py - y1), 0.0)

    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))

    cx = x1 + t * dx
    cy = y1 + t * dy

    return (math.hypot(px - cx, py - cy), t)
