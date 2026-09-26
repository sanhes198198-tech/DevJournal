"""
Attachment - временный контейнер для описания одного endpoint.

target_type: "anchor" | "mountpoint"
target_id:   legacy alias или id MountPoint
location:    {"x": int, "y": int} | None (только для mountpoint)
child_anchor: legacy поле связи, сохранено для совместимости
"""

from __future__ import annotations


VALID_TARGET_TYPES = ("anchor", "mountpoint")


def endpoint_from_component_value(
    value: str | None,
    *,
    field: str,
) -> dict | None:
    """Adapt a legacy Component endpoint string to a temporary descriptor.

    This helper only classifies and parses the stored string. It does not
    resolve endpoints, inspect an Asset, or mutate the Component.
    """
    if value is None or value == "":
        return None

    if field == "attach_anchor":
        return {
            "kind": "legacy_anchor",
            "alias": value,
            "raw_value": value,
        }

    if field != "parent_anchor":
        raise ValueError(
            "field must be 'attach_anchor' or 'parent_anchor'"
        )

    if value.startswith("slot_"):
        return {
            "kind": "legacy_slot",
            "raw_value": value,
        }

    if value.startswith("mp_"):
        parts = value.split("__")
        if len(parts) == 3 and parts[0].startswith("mp_"):
            try:
                index_x = int(parts[1])
                index_y = int(parts[2])
            except ValueError:
                pass
            else:
                return {
                    "kind": "native_mountpoint",
                    "mountpoint_id": parts[0],
                    "index_x": index_x,
                    "index_y": index_y,
                    "raw_value": value,
                }

        # Keep malformed MountPoint-looking values diagnostic-only. They
        # must not be treated as aliases or passed to Attachment.resolve().
        return {
            "kind": None,
            "raw_value": value,
        }

    return {
        "kind": "legacy_anchor",
        "alias": value,
        "raw_value": value,
    }


class Attachment:
    """Связь компонента с родителем."""

    def __init__(
        self,
        target_type: str = "",
        target_id: str = "",
        location: dict | None = None,
        child_anchor: str = "",
    ):
        self.target_type: str = str(target_type or "")
        self.target_id: str = str(target_id or "")
        self.location: dict | None = (
            dict(location) if location else None
        )
        self.child_anchor: str = str(child_anchor or "")

    # ------------------------------------------------------------

    def is_valid(self) -> bool:
        if self.target_type not in VALID_TARGET_TYPES:
            return False
        if not self.target_id:
            return False
        if self.target_type == "mountpoint":
            if not isinstance(self.location, dict):
                return False
            if "x" not in self.location or "y" not in self.location:
                return False
        return True

    def is_anchor(self) -> bool:
        return self.target_type == "anchor"

    def is_mountpoint(self) -> bool:
        return self.target_type == "mountpoint"

    def resolve(self, asset, bbox=None) -> tuple[tuple[float, float], str]:
        """Разрешить endpoint в локальную координату Asset.

        Возвращает ``(position, source)``, где source равен
        ``"native_mountpoint"`` или ``"legacy_anchor"``.

        Для MountPoint location содержит индексы ``x`` и ``y``.
        Для legacy anchor target_id — alias, разрешаемый только через
        ``Asset.anchors()``. Этот метод не сохраняет и не меняет данные.

        Raises:
            ValueError: если endpoint неизвестен, некорректен или не может
                быть разрешён в переданном Asset.
        """
        if not self.target_id:
            raise ValueError("Endpoint target_id is required")

        if self.is_anchor():
            anchors = asset.anchors()
            position = anchors.get(self.target_id)
            if position is None:
                raise ValueError(
                    f"Unknown legacy anchor alias: {self.target_id!r}"
                )
            return (
                (float(position[0]), float(position[1])),
                "legacy_anchor",
            )

        if not self.is_mountpoint():
            raise ValueError(
                f"Unknown endpoint target_type: {self.target_type!r}"
            )

        if not isinstance(self.location, dict):
            raise ValueError("MountPoint endpoint requires location indices")
        try:
            index_x = self.location["x"]
            index_y = self.location["y"]
        except KeyError as exc:
            raise ValueError(
                "MountPoint endpoint requires x and y indices"
            ) from exc
        if (
            isinstance(index_x, bool)
            or not isinstance(index_x, int)
            or isinstance(index_y, bool)
            or not isinstance(index_y, int)
        ):
            raise ValueError("MountPoint indices must be integers")

        mountpoint = next(
            (
                mp for mp in (getattr(asset, "mountpoints", None) or [])
                if mp.id == self.target_id
            ),
            None,
        )
        if mountpoint is None:
            raise ValueError(f"Unknown MountPoint: {self.target_id!r}")

        if mountpoint.anchor_mode == "relative_xy":
            if bbox is None or len(bbox) != 4:
                raise ValueError(
                    "A four-value bbox is required for relative_xy MountPoint"
                )
        try:
            locations = mountpoint.resolve(bbox=bbox)
        except Exception as exc:
            raise ValueError(
                f"Could not resolve MountPoint {self.target_id!r}: {exc}"
            ) from exc

        for location in locations:
            if (
                location.index_x == index_x
                and location.index_y == index_y
            ):
                return (
                    (float(location.position[0]), float(location.position[1])),
                    "native_mountpoint",
                )

        raise ValueError(
            f"Invalid MountPoint location index: "
            f"({index_x}, {index_y}) for {self.target_id!r}"
        )

    # ------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "target_type": self.target_type,
            "target_id": self.target_id,
            "location": (
                dict(self.location) if self.location else None
            ),
            "child_anchor": self.child_anchor,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Attachment":
        if not isinstance(d, dict):
            raise ValueError("Attachment.from_dict: dict expected")

        loc = d.get("location")
        if loc is not None and not isinstance(loc, dict):
            loc = None

        return cls(
            target_type=d.get("target_type", ""),
            target_id=d.get("target_id", ""),
            location=loc,
            child_anchor=d.get("child_anchor", ""),
        )

    def __repr__(self) -> str:
        return (
            f"Attachment(type={self.target_type!r} "
            f"id={self.target_id!r} "
            f"loc={self.location} "
            f"child={self.child_anchor!r})"
        )
