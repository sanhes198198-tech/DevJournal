"""
Геометрические операции над контуром.

Чистая математика, без Qt.
"""

from __future__ import annotations

import math


def extrude_face(
    points: list[tuple[float, float]],
    seg_idx: int,
    distance: float,
) -> list[tuple[float, float]] | None:
    """Вытянуть грань (points[seg_idx] → points[seg_idx+1]) наружу по нормали.

    Возвращает НОВЫЙ список точек или None, если операция невозможна.

    Логика:
      - нормаль — перпендикуляр к грани, направленный ОТ центроида;
      - обе вершины грани смещаются на distance по этой нормали;
      - в контур вставляются две новые точки сразу после points[seg_idx].

    Пример:
      было:  A ─── B
             │     │
             D ─── C

      extrude(C → D):
             A ─── B
             │     │
             D ─── C     ← сегмент становится "швом"
             │     │
             D' ── C'    ← новые точки вставлены
    """
    n = len(points)
    if n < 3 or seg_idx < 0 or seg_idx >= n:
        return None

    p1 = points[seg_idx]
    p2 = points[(seg_idx + 1) % n]

    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length < 1e-9:
        return None

    # Перпендикуляр (один из двух возможных)
    nx = dy / length
    ny = -dx / length

    # Определяем направление "наружу" — от центроида к середине грани
    cx = sum(p[0] for p in points) / n
    cy = sum(p[1] for p in points) / n

    mx = (p1[0] + p2[0]) / 2.0
    my = (p1[1] + p2[1]) / 2.0

    if nx * (mx - cx) + ny * (my - cy) < 0.0:
        nx = -nx
        ny = -ny

    p1_new = (p1[0] + nx * distance, p1[1] + ny * distance)
    p2_new = (p2[0] + nx * distance, p2[1] + ny * distance)

    # Вставляем сразу после p1: [... p1, p1_new, p2_new, p2, ...]
    new_points = (
        points[:seg_idx + 1]
        + [p1_new, p2_new]
        + points[seg_idx + 1:]
    )
    return new_points
