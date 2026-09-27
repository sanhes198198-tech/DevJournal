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

from app.vector_editor.model.mounting.attachment import (
    endpoint_from_component_value,
)


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
        attachment = getattr(child_comp, "attachment", None)
        legacy_parent_id = getattr(child_comp, "attach_to", "")
        attached_parent_id = getattr(
            attachment, "parent_component_id", legacy_parent_id,
        )
        if attached_parent_id != parent_id:
            continue

        native_parent_location = getattr(
            attachment, "parent_location", None,
        )
        if not isinstance(native_parent_location, dict):
            native_parent_location = getattr(
                child_comp, "parent_location", None,
            )
        if isinstance(native_parent_location, dict):
            mp_id = native_parent_location.get("mountpoint_id")
            ix = native_parent_location.get("index_x")
            iy = native_parent_location.get("index_y")
            if (
                not isinstance(mp_id, str)
                or not mp_id
                or isinstance(ix, bool)
                or not isinstance(ix, int)
                or isinstance(iy, bool)
                or not isinstance(iy, int)
            ):
                continue
        else:
            # Compatibility for older composites whose native parent
            # address is still encoded in parent_anchor.
            endpoint = endpoint_from_component_value(
                child_comp.parent_anchor,
                field="parent_anchor",
            )
            if (
                endpoint is None
                or endpoint.get("kind") != "native_mountpoint"
            ):
                continue
            mp_id = endpoint["mountpoint_id"]
            ix = endpoint["index_x"]
            iy = endpoint["index_y"]

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
        child_location = getattr(attachment, "child_location", None)
        if not isinstance(child_location, dict):
            child_location = getattr(child_comp, "attach_location", None)
        child_alias = (
            None if isinstance(child_location, dict)
            else child_comp.attach_anchor
        )
        endpoint = child_item.resolve_child_endpoint(child_alias)
        if endpoint is None or not endpoint.get("resolved"):
            continue
        c_local = endpoint.get("local_position")
        if c_local is None:
            continue

        # Use the child's actual Qt transform, just as Snap does. Subtracting
        # an item-local endpoint directly ignores child rotation and scale.
        parent_scene = parent_item.mapToScene(
            QPointF(p_local[0], p_local[1])
        )
        new_position = child_item.position_for_endpoint_at_scene(
            c_local, parent_scene,
        )
        new_x = new_position.x()
        new_y = new_position.y()

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
