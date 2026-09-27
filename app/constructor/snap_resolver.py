"""
SnapResolver — поиск ближайшего MountLocation для компонента.

Отдельный модуль, чтобы ComponentItem._try_snap не занимался поиском.
Не хранит состояния — чистая функция find_mount_snap().
"""
from __future__ import annotations


class SnapResult:
    """Результат поиска: что нашли и куда сдвинуться."""

    __slots__ = (
        "other_item", "my_tag", "my_location", "their_tag",
        "their_location", "dx", "dy",
    )

    def __init__(
        self,
        other_item,
        my_tag: str | None,
        their_tag: str,
        dx: float,
        dy: float,
        my_location: dict | None = None,
        their_location: dict | None = None,
    ):
        self.other_item = other_item
        self.my_tag = my_tag
        self.my_location = (
            dict(my_location) if isinstance(my_location, dict) else None
        )
        self.their_tag = their_tag
        self.their_location = (
            dict(their_location)
            if isinstance(their_location, dict)
            else None
        )
        self.dx = dx
        self.dy = dy


def find_mount_snap(
    scene,
    my_item,
    my_bottom,
    role_str: str,
    threshold_m: float,
    component_item_cls,
    *,
    my_tag: str | None = "bottom",
    my_location: dict | None = None,
) -> SnapResult | None:
    """Найти ближайший MountLocation с ролью role_str на соседних item.

    Возвращает SnapResult(other_item, my_tag, their_tag, dx, dy) или None.
    """
    my_comp = getattr(my_item, "_component", None)
    if my_comp is None:
        return None

    mx, my = my_bottom
    best = None  # (dist, other, their_tag, their_location, dx, dy)

    for other in scene.items():
        if other is my_item:
            continue
        if not isinstance(other, component_item_cls):
            continue
        o_comp = getattr(other, "_component", None)
        if o_comp is None:
            continue
        if o_comp.id == my_comp.id:
            continue
        other_attachment = getattr(o_comp, "attachment", None)
        legacy_parent_id = getattr(o_comp, "attach_to", "")
        other_parent_id = getattr(
            other_attachment, "parent_component_id", legacy_parent_id,
        )
        if other_parent_id == my_comp.id:
            continue

        try:
            locs = other.mount_locations_by_role(role_str)
        except Exception:
            locs = []

        for mp_id, ix, iy, sx, sy in locs:
            dx = sx - mx
            dy = sy - my
            dist = (dx * dx + dy * dy) ** 0.5
            if dist <= threshold_m:
                if best is None or dist < best[0]:
                    their_tag = f"{mp_id}__{ix}__{iy}"
                    their_location = {
                        "mountpoint_id": mp_id,
                        "index_x": ix,
                        "index_y": iy,
                    }
                    best = (
                        dist, other, their_tag, their_location, dx, dy,
                    )

    if best is None:
        return None
    _, other, their_tag, their_location, dx, dy = best
    return SnapResult(
        other,
        my_tag,
        their_tag,
        dx,
        dy,
        my_location=my_location,
        their_location=their_location,
    )

def find_wall_snap(
    scene,
    my_item,
    threshold_m: float,
    component_item_cls,
) -> SnapResult | None:
    """Найти ближайшую стену для соединения низ↔верх.

    Логика:
      - у my_item ищем группу "mount_bottom" (её низ)
      - у соседних ищем группу "mount_top" (их верх)
      - если центр моего низа близко к центру их верха → snap

    Возвращает SnapResult или None. my_tag = "mount_bottom",
    their_tag = "wall_top__<comp_id>".
    """
    my_comp = getattr(my_item, "_component", None)
    if my_comp is None:
        return None

    my_bottom_resolver = getattr(my_item, "group_bbox_world", None)
    if not callable(my_bottom_resolver):
        return None

    my_bbox = my_bottom_resolver("mount_bottom")
    if my_bbox is None:
        return None

    mxmin, mymin, mxmax, mymax = my_bbox
    mx = (mxmin + mxmax) / 2.0
    my = (mymin + mymax) / 2.0

    best = None  # (dist, other, their_tag, dx, dy)

    for other in scene.items():
        if other is my_item:
            continue
        if not isinstance(other, component_item_cls):
            continue
        o_comp = getattr(other, "_component", None)
        if o_comp is None:
            continue
        if o_comp.id == my_comp.id:
            continue
        # Не привязываемся к тому, кто уже привязан к нам
        # НЕ пропускаем соседа, даже если он привязан к нам —
        # иначе не сможем поменять местами (A↔Б).
        # Cycle-break делается в _try_snap.

        their_resolver = getattr(other, "group_bbox_world", None)
        if not callable(their_resolver):
            continue
        their_bbox = their_resolver("mount_top")
        if their_bbox is None:
            continue


        txmin, tymin, txmax, tymax = their_bbox
        tx = (txmin + txmax) / 2.0
        ty = (tymin + tymax) / 2.0

        dx = tx - mx
        dy = ty - my
        dist = (dx * dx + dy * dy) ** 0.5

        if dist <= threshold_m:
            if best is None or dist < best[0]:
                their_tag = f"wall_top__{o_comp.id}"
                best = (dist, other, their_tag, dx, dy)

    if best is None:
        return None
    _, other, their_tag, dx, dy = best
    return SnapResult(
        other,
        "mount_bottom",
        their_tag,
        dx,
        dy,
    )

