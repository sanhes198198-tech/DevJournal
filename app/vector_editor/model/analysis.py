"""
Геометрический анализ контура для автогенерации групп.

Чистая математика, без Qt. Работает с точками и node_ids.

Все функции принимают:
    points: list[tuple[float, float]]
    node_ids: list[str]   (параллельный points)

Возвращают: list[str] — node_ids.
"""

from __future__ import annotations


HORIZ_TOL = 0.5       # метров — ребро «горизонтально», если |dy| < 0.5
VERT_TOL = 0.5        # ребро «вертикально», если |dx| < 0.5
CROSS_TOL = 1e-4      # для определения угла выпуклости


# ============================================================
# HORIZONTAL / VERTICAL EDGES
# ============================================================

def find_horizontal_edge_nodes(
    points: list[tuple[float, float]],
    node_ids: list[str],
    tolerance: float = HORIZ_TOL,
) -> list[str]:
    """Узлы, инцидентные хотя бы одному горизонтальному ребру.

    Горизонтальное = y обеих точек ребра совпадают (± tolerance).
    """
    n = len(points)
    if n < 2:
        return []

    result: set[str] = set()
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        if abs(y1 - y2) < tolerance:
            # не считаем "точка", если ребро нулевой длины
            if abs(x1 - x2) < tolerance:
                continue
            result.add(node_ids[i])
            result.add(node_ids[(i + 1) % n])

    return sorted(result)


def find_vertical_edge_nodes(
    points: list[tuple[float, float]],
    node_ids: list[str],
    tolerance: float = VERT_TOL,
) -> list[str]:
    """Узлы, инцидентные хотя бы одному вертикальному ребру."""
    n = len(points)
    if n < 2:
        return []

    result: set[str] = set()
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        if abs(x1 - x2) < tolerance:
            if abs(y1 - y2) < tolerance:
                continue
            result.add(node_ids[i])
            result.add(node_ids[(i + 1) % n])

    return sorted(result)


# ============================================================
# CONVEX / CONCAVE
# ============================================================

def _signed_area(points: list[tuple[float, float]]) -> float:
    """Shoelace. >0 → CCW, <0 → CW."""
    n = len(points)
    if n < 3:
        return 0.0
    s = 0.0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def _cross(p, p_prev, p_next) -> float:
    """Cross product (p - p_prev) × (p_next - p).
    >0 — поворот налево, <0 — направо.
    """
    v1x = p[0] - p_prev[0]
    v1y = p[1] - p_prev[1]
    v2x = p_next[0] - p[0]
    v2y = p_next[1] - p[1]
    return v1x * v2y - v1y * v2x


def find_convex_nodes(
    points: list[tuple[float, float]],
    node_ids: list[str],
) -> list[str]:
    """Выпуклые вершины.

    Ориентация контура определяется автоматически.
    """
    n = len(points)
    if n < 3:
        return []

    area = _signed_area(points)
    if abs(area) < 1e-9:
        # Вырожденный контур
        return []

    ccw = area > 0
    result = []

    for i in range(n):
        p_prev = points[(i - 1) % n]
        p = points[i]
        p_next = points[(i + 1) % n]

        cross = _cross(p, p_prev, p_next)
        if abs(cross) < CROSS_TOL:
            continue

        is_convex = (cross > 0) if ccw else (cross < 0)
        if is_convex:
            result.append(node_ids[i])

    return result


def find_concave_nodes(
    points: list[tuple[float, float]],
    node_ids: list[str],
) -> list[str]:
    """Вогнутые вершины."""
    n = len(points)
    if n < 3:
        return []

    area = _signed_area(points)
    if abs(area) < 1e-9:
        return []

    ccw = area > 0
    result = []

    for i in range(n):
        p_prev = points[(i - 1) % n]
        p = points[i]
        p_next = points[(i + 1) % n]

        cross = _cross(p, p_prev, p_next)
        if abs(cross) < CROSS_TOL:
            continue

        is_concave = (cross < 0) if ccw else (cross > 0)
        if is_concave:
            result.append(node_ids[i])

    return result


# ============================================================
# TYPES
# ============================================================

AUTO_GROUP_TYPES = (
    ("horizontal", "Горизонтальные рёбра",
     "auto_horizontal"),
    ("vertical", "Вертикальные рёбра",
     "auto_vertical"),
    ("convex", "Выпуклые вершины",
     "auto_convex"),
    ("concave", "Вогнутые вершины",
     "auto_concave"),
)


def generate_auto_group(
    kind: str,
    points: list[tuple[float, float]],
    node_ids: list[str],
) -> list[str]:
    """Универсальный вызов по типу."""
    if kind == "horizontal":
        return find_horizontal_edge_nodes(points, node_ids)
    if kind == "vertical":
        return find_vertical_edge_nodes(points, node_ids)
    if kind == "convex":
        return find_convex_nodes(points, node_ids)
    if kind == "concave":
        return find_concave_nodes(points, node_ids)
    return []
