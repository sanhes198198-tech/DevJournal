"""
ReflowEngine — правильный repositioning детей при движении родителя.

Когда Component X (стена) сдвинулся, все компоненты, привязанные
к его mount-точкам (parent_anchor = mp_xxx__ix__iy), должны ехать
за той же точкой.

Отличие от старого _reflow_children:
  - только mount-attachment (не anchor, не slot)
  - чистая функция без состояния
  - не мутирует модель attachment
  - поддержка рекурсии (дети детей)
"""
from __future__ import annotations

from PySide6.QtCore import QPointF


def _parse_mount_tag(tag: str) -> tuple[str, int, int] | None:
    """Парсит 'mp_xxx__ix__iy' → (mp_id, ix, iy). Или None."""
    parts = tag.split("__")
    if len(parts) != 3:
        return None
    if not parts[0].startswith("mp_"):
        return None
    try:
        return parts[0], int(parts[1]), int(parts[2])
    except ValueError:
        return None


def reflow_from(
    parent_id: str,
    items_by_comp_id: dict,
    composite,
) -> int:
    """Пересчитать позиции всех mount-привязанных детей родителя.

    Возвращает число пересчитанных компонентов.
    """
    if composite is None:
        return 0
    visited: set[str] = set()
    return _reflow_recursive(parent_id, items_by_comp_id, composite, visited)


def _reflow_recursive(
    parent_id: str,
    items_by_comp_id: dict,
    composite,
    visited: set,
) -> int:
    if parent_id in visited:
        return 0
    visited.add(parent_id)

    parent_item = items_by_comp_id.get(parent_id)
    if parent_item is None:
        return 0

    count = 0
    for child_id, child_item in list(items_by_comp_id.items()):
        if child_id in visited:
            continue
        child_comp = composite.get_component(child_id)
        if child_comp is None:
            continue
        if child_comp.attach_to != parent_id:
            continue

        tag = getattr(child_comp, "parent_anchor", "") or ""
        parsed = _parse_mount_tag(tag)
        if parsed is None:
            continue
        mp_id, ix, iy = parsed

        # mount location в локальных координатах родителя
        mp_local = parent_item.mount_locations_local()
        arr = mp_local.get(mp_id, [])
        p_local = None
        for lx_ix, lx_iy, _role, lx, ly in arr:
            if lx_ix == ix and lx_iy == iy:
                p_local = (lx, ly)
                break
        if p_local is None:
            continue

        # anchor ребёнка в его локальных координатах
        child_anchors = child_item.anchors_local()
        c_local = child_anchors.get(child_comp.attach_anchor)
        if c_local is None:
            continue

        # новая позиция = mount_world - child_anchor_local
        parent_scene = parent_item.mapToScene(
            QPointF(p_local[0], p_local[1])
        )
        new_x = parent_scene.x() - c_local[0]
        new_y = parent_scene.y() - c_local[1]

        if (abs(child_comp.x - new_x) > 1e-9
                or abs(child_comp.y - new_y) > 1e-9):
            child_comp.x = new_x
            child_comp.y = new_y
            child_item.setPos(new_x, new_y)
            child_item.update()
            count += 1

        # рекурсия — дети ребёнка тоже едут
        count += _reflow_recursive(
            child_id, items_by_comp_id, composite, visited,
        )

    return count