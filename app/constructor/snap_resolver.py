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
    """Ищет ближайшее соединение стен (вертикаль или горизонталь).

    Пары ролей:
      - mount_bottom ↔ mount_top  (я сверху, цепляюсь к нижнему соседу)
      - mount_top    ↔ mount_bottom (я снизу, цепляюсь к верхнему)
      - mount_left   ↔ mount_right  (я справа, цепляюсь к левому)
      - mount_right  ↔ mount_left   (я слева, цепляюсь к правому)

    Побеждает ближайшая пара. my_tag = "mount_XXX", their_tag =
    "wall_YYY__<other_id>".
    """
    my_comp = getattr(my_item, "_component", None)
    if my_comp is None:
        return None

    my_resolver = getattr(my_item, "group_bbox_world", None)
    if not callable(my_resolver):
        return None

    pairs = (
        ("mount_bottom", "mount_top"),
        ("mount_top", "mount_bottom"),
        ("mount_left", "mount_right"),
        ("mount_right", "mount_left"),
    )

    best = None  # (dist, other, my_group, their_group, dx, dy)

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

        their_resolver = getattr(other, "group_bbox_world", None)
        if not callable(their_resolver):
            continue

        for my_group, their_group in pairs:
            my_bbox = my_resolver(my_group)
            if my_bbox is None:
                continue
            their_bbox = their_resolver(their_group)
            if their_bbox is None:
                continue

            mx = (my_bbox[0] + my_bbox[2]) / 2.0
            my = (my_bbox[1] + my_bbox[3]) / 2.0
            tx = (their_bbox[0] + their_bbox[2]) / 2.0
            ty = (their_bbox[1] + their_bbox[3]) / 2.0

            dx = tx - mx
            dy = ty - my
            dist = (dx * dx + dy * dy) ** 0.5

            if dist <= threshold_m:
                if best is None or dist < best[0]:
                    best = (
                        dist, other, my_group, their_group, dx, dy,
                    )

    if best is None:
        return None

    _, other, my_group, their_group, dx, dy = best
    o_comp = getattr(other, "_component", None)
    # Формат их тега: mount_top -> wall_top, mount_left -> wall_left
    suffix = their_group.replace("mount_", "wall_")
    their_tag = f"{suffix}__{o_comp.id}"

    return SnapResult(
        other,
        my_group,
        their_tag,
        dx,
        dy,
    )
