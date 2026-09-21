"""
V9b: авто-генерация точек на группах с auto_rule.

Пользователь ставит одну extra-точку-шаблон, создаёт группу
с этой точкой, задаёт auto_rule. При изменении параметров
(например height) - точки автоматически дублируются с шагом
вдоль оси, пока не дойдут до границы (until_group).

Правило:
{
    "axis": "y",           # ось размножения ("x" или "y")
    "step": -3.0,          # шаг со знаком (минус = вверх для Y)
    "until_group": "top",  # имя группы-границы (центроид = предел)
    "skip_groups": [],     # группы, где НЕ ставить точки
    "max_count": 200,      # защита от бесконечного цикла
}
"""
from __future__ import annotations


AUTO_PREFIX = "e_auto_"


def recalculate_auto_points(contour, semantic_groups) -> int:
    """Пересчитать авто-точки во всех группах с auto_rule.

    contour - объект с полями:
        points, node_ids, extra_points, extra_node_ids
    semantic_groups - dict gid -> SemanticGroup

    Пишет в contour.extra_points / extra_node_ids.
    Также обновляет node_ids внутри групп.

    Возвращает количество добавленных точек.
    """
    # 1. Удалить существующие auto-точки из contour
    keep_pts = []
    keep_ids = []
    for i, nid in enumerate(contour.extra_node_ids):
        if not nid.startswith(AUTO_PREFIX):
            keep_pts.append(contour.extra_points[i])
            keep_ids.append(nid)
    contour.extra_points = keep_pts
    contour.extra_node_ids = keep_ids

    # 2. Удалить auto-точки из всех групп
    for group in semantic_groups.values():
        group.node_ids = [
            nid for nid in group.node_ids
            if not nid.startswith(AUTO_PREFIX)
        ]

    # 3. Индекс позиций
    pts_by_id = _build_pts_by_id(contour)

    # 4. Для каждой группы с auto_rule - генерировать
    added = 0
    for gid, group in semantic_groups.items():
        rule = getattr(group, "auto_rule", None)
        if not rule:
            continue
        if not group.node_ids:
            continue

        template_id = group.node_ids[0]
        template_pos = pts_by_id.get(template_id)
        if template_pos is None:
            continue

        axis = rule.get("axis", "y")
        step = float(rule.get("step", 1.0))
        if abs(step) < 1e-9:
            continue

        axis_idx = 0 if axis == "x" else 1

        until_name = rule.get("until_group") or ""
        # Без границы авто-размножение бессмысленно — оно
        # сгенерирует сотни точек и растянет ассет.
        if not until_name:
            continue

        limit_val = _find_limit(
            until_name, axis_idx,
            semantic_groups, pts_by_id,
        )
        if limit_val is None:
            # Граница задана, но группы нет — не генерируем.
            continue

        # Ограничение сверху, чтобы не убить ассет.
        max_count = int(rule.get("max_count", 30))

        skip_boxes = _skip_boxes(
            rule.get("skip_groups", []),
            semantic_groups, pts_by_id,
        )

        current = template_pos[axis_idx] + step
        counter = 0
        while counter < max_count:
            if limit_val is not None:
                # Граница — эксклюзивная: точка, попавшая ровно
                # на until_group, не добавляется.
                if step > 0 and current >= limit_val:
                    break
                if step < 0 and current <= limit_val:
                    break

            new_pt = list(template_pos)
            new_pt[axis_idx] = current

            if not _in_skip_boxes(new_pt, skip_boxes):
                new_id = f"{AUTO_PREFIX}{gid}_{counter:02d}"
                contour.extra_points.append(new_pt)
                contour.extra_node_ids.append(new_id)
                group.node_ids.append(new_id)
                pts_by_id[new_id] = tuple(new_pt)
                added += 1

            current += step
            counter += 1

    return added


def _build_pts_by_id(contour) -> dict:
    pts = {}
    for i, nid in enumerate(contour.node_ids):
        if i < len(contour.points):
            x, y = contour.points[i]
            pts[nid] = (float(x), float(y))
    for i, nid in enumerate(contour.extra_node_ids):
        if i < len(contour.extra_points):
            x, y = contour.extra_points[i]
            pts[nid] = (float(x), float(y))
    return pts


def _group_centroid(group, pts_by_id):
    xs, ys = [], []
    for nid in group.node_ids:
        p = pts_by_id.get(nid)
        if p is not None:
            xs.append(p[0])
            ys.append(p[1])
    if not xs:
        return None
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _find_group_by_name(semantic_groups, name):
    if not name:
        return None
    for g in semantic_groups.values():
        if g.name == name:
            return g
    return None


def _find_limit(name, axis_idx, semantic_groups, pts_by_id):
    if not name:
        return None
    g = _find_group_by_name(semantic_groups, name)
    if g is None:
        return None
    c = _group_centroid(g, pts_by_id)
    if c is None:
        return None
    return c[axis_idx]


def _skip_boxes(names, semantic_groups, pts_by_id):
    boxes = []
    for name in names:
        g = _find_group_by_name(semantic_groups, name)
        if g is None:
            continue
        xs, ys = [], []
        for nid in g.node_ids:
            p = pts_by_id.get(nid)
            if p is not None:
                xs.append(p[0])
                ys.append(p[1])
        if xs:
            boxes.append((min(xs), min(ys), max(xs), max(ys)))
    return boxes


def _in_skip_boxes(pt, boxes):
    x, y = pt[0], pt[1]
    for (x0, y0, x1, y1) in boxes:
        if x0 <= x <= x1 and y0 <= y <= y1:
            return True
    return False