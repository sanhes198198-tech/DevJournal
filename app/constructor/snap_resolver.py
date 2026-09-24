"""
SnapResolver — поиск ближайшего MountLocation для компонента.

Отдельный модуль, чтобы ComponentItem._try_snap не занимался поиском.
Не хранит состояния — чистая функция find_mount_snap().
"""
from __future__ import annotations


class SnapResult:
    """Результат поиска: что нашли и куда сдвинуться."""

    __slots__ = ("other_item", "my_tag", "their_tag", "dx", "dy")

    def __init__(self, other_item, my_tag, their_tag, dx, dy):
        self.other_item = other_item
        self.my_tag = my_tag
        self.their_tag = their_tag
        self.dx = dx
        self.dy = dy


def find_mount_snap(
    scene,
    my_item,
    my_bottom,
    role_str: str,
    threshold_m: float,
    component_item_cls,
) -> SnapResult | None:
    """Найти ближайший MountLocation с ролью role_str на соседних item.

    Возвращает SnapResult(other_item, "bottom", their_tag, dx, dy) или None.
    """
    my_comp = getattr(my_item, "_component", None)
    if my_comp is None:
        return None

    mx, my = my_bottom
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
        if o_comp.attach_to == my_comp.id:
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
                    best = (dist, other, their_tag, dx, dy)

    if best is None:
        return None
    _, other, their_tag, dx, dy = best
    return SnapResult(other, "bottom", their_tag, dx, dy)