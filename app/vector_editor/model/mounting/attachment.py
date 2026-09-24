"""
Attachment - структурированная связь child-компонента с родителем.

target_type: "anchor" | "mountpoint"
target_id:   id anchor или id MountPoint
location:    {"x": int, "y": int} | None (только для mountpoint)
child_anchor: наш anchor (bottom / top / ...)
"""

from __future__ import annotations


VALID_TARGET_TYPES = ("anchor", "mountpoint")


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