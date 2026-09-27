"""
Component — ссылка на другой Asset внутри составного Asset'а.

Пример: башня состоит из [стена, купол, окно_1, окно_2].
Каждый — Component: ссылка на asset_id + позиция/поворот/масштаб.

Модель чистая, без Qt.
"""

from __future__ import annotations

import uuid

from .mounting import Attachment, MountRole, parse_role, role_to_str
from .mounting.attachment import endpoint_from_component_value


class Component:
    """Один компонент составного Asset'а."""

    def __init__(
        self,
        id: str | None = None,
        asset_id: str = "",
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
        scale: float = 1.0,
        name: str = "",
        layer: int = 0,
        filled: bool = False,
        param_overrides: dict | None = None,
        attach_to: str = "",
        attach_anchor: str | None = "",
        parent_anchor: str = "",
        fill_pattern: str = "",
        locked: bool = False,
        role: MountRole | str | None = None,
        attach_location: dict | None = None,
        parent_location: dict | None = None,
    ):
        self.id = id or self._generate_id()
        self.asset_id = asset_id
        self.x = float(x)
        self.y = float(y)
        self.rotation = float(rotation)
        self.scale = float(scale) if scale > 0 else 1.0
        self.name = name
        self.layer = int(layer)
        self.filled = bool(filled)
        # Локальные переопределения параметров sub-ассета.
        # {param_name: value}
        self.param_overrides: dict[str, float] = dict(
            param_overrides or {}
        )
        # Legacy endpoint aliases remain as compatibility/persistence data.
        self._attach_anchor: str | None = (
            None if attach_anchor is None else str(attach_anchor)
        )
        self._parent_anchor: str = str(parent_anchor or "")

        # Old composites may encode a native parent MountLocation in the
        # parent_anchor string. Adapt it into the unified relationship while
        # retaining the original string as compatibility data.
        native_parent_location = (
            dict(parent_location) if isinstance(parent_location, dict) else None
        )
        self._parent_location_from_legacy_tag = False
        if native_parent_location is None:
            descriptor = endpoint_from_component_value(
                self._parent_anchor,
                field="parent_anchor",
            )
            if descriptor and descriptor.get("kind") == "native_mountpoint":
                native_parent_location = {
                    "mountpoint_id": descriptor["mountpoint_id"],
                    "index_x": descriptor["index_x"],
                    "index_y": descriptor["index_y"],
                }
                self._parent_location_from_legacy_tag = True

        # One model object owns the parent component reference and both native
        # endpoint addresses. Existing flat Component fields below remain
        # compatibility properties for runtime callers and JSON persistence.
        self.attachment = Attachment(
            parent_component_id=attach_to,
            parent_location=native_parent_location,
            child_location=attach_location,
        )
        # V11: текстура заливки. "" = без текстуры.
        # "hatch" = серая диагональная штриховка.
        # "diamonds" = ромбы (косой крест).
        self.fill_pattern: str = str(fill_pattern or "")
        # V12: блокировка перемещения и параметров.
        # Заблокированный можно выделить и удалить, но нельзя
        # двигать (drag) и менять height/width через панель.
        self.locked: bool = bool(locked)

        # V22 (Mounting): роль компонента в композите.
        # Отдельно от asset.type. None = не привязан к роли.
        self.role: MountRole | None = parse_role(role)

    @staticmethod
    def _generate_id() -> str:
        return "c_" + uuid.uuid4().hex[:8]

    # ------------------------------------------------------------

    def is_valid(self) -> bool:
        """Базовая валидация: есть ссылка на asset."""
        return bool(self.asset_id)

    # ------------------------------------------------------------
    # ATTACHMENT COMPATIBILITY PROPERTIES
    # ------------------------------------------------------------

    @property
    def attach_to(self) -> str:
        return self.attachment.parent_component_id

    @attach_to.setter
    def attach_to(self, value: str | None) -> None:
        self.attachment.parent_component_id = str(value or "")

    @property
    def attach_location(self) -> dict | None:
        return self.attachment.child_location

    @attach_location.setter
    def attach_location(self, value: dict | None) -> None:
        self.attachment.child_location = (
            dict(value) if isinstance(value, dict) else None
        )

    @property
    def parent_location(self) -> dict | None:
        return self.attachment.parent_location

    @parent_location.setter
    def parent_location(self, value: dict | None) -> None:
        self.attachment.parent_location = (
            dict(value) if isinstance(value, dict) else None
        )
        self._parent_location_from_legacy_tag = False

    @property
    def attach_anchor(self) -> str | None:
        return self._attach_anchor

    @attach_anchor.setter
    def attach_anchor(self, value: str | None) -> None:
        self._attach_anchor = None if value is None else str(value)

    @property
    def parent_anchor(self) -> str:
        return self._parent_anchor

    @parent_anchor.setter
    def parent_anchor(self, value: str | None) -> None:
        self._parent_anchor = str(value or "")
        attachment = getattr(self, "attachment", None)
        if attachment is None:
            return
        if self._parent_location_from_legacy_tag:
            attachment.parent_location = None
            self._parent_location_from_legacy_tag = False
        if attachment.parent_location is not None:
            return
        descriptor = endpoint_from_component_value(
            self._parent_anchor,
            field="parent_anchor",
        )
        if descriptor and descriptor.get("kind") == "native_mountpoint":
            attachment.parent_location = {
                "mountpoint_id": descriptor["mountpoint_id"],
                "index_x": descriptor["index_x"],
                "index_y": descriptor["index_y"],
            }
            self._parent_location_from_legacy_tag = True

    # ------------------------------------------------------------
    # PARAM OVERRIDES
    # ------------------------------------------------------------

    def set_param_override(self, name: str, value: float) -> None:
        self.param_overrides[name] = float(value)

    def get_param_override(self, name: str) -> float | None:
        return self.param_overrides.get(name)

    def clear_param_override(self, name: str) -> bool:
        return self.param_overrides.pop(name, None) is not None

    def clear_all_overrides(self) -> None:
        self.param_overrides.clear()

    # ------------------------------------------------------------
    # ATTACH (V11)
    # ------------------------------------------------------------

    def set_attachment(
        self, parent_id: str,
        attach_anchor: str | None, parent_anchor: str | None,
        *, attach_location: dict | None = None,
        parent_location: dict | None = None,
    ) -> None:
        """Прикрепить этот компонент к родителю."""
        self.attach_to = str(parent_id)
        if isinstance(attach_location, dict):
            self.attach_location = dict(attach_location)
        elif attach_anchor is not None:
            self.attach_anchor = str(attach_anchor)
        if isinstance(parent_location, dict):
            self.parent_location = dict(parent_location)
        elif parent_anchor is not None:
            self.parent_anchor = str(parent_anchor)

    def clear_attachment(self) -> None:
        self.attach_to = ""
        self.attach_anchor = ""
        self.parent_anchor = ""
        self.attach_location = None
        self.parent_location = None

    def to_dict(self) -> dict:
        data = {
            "id": self.id,
            "asset_id": self.asset_id,
            "x": self.x,
            "y": self.y,
            "rotation": self.rotation,
            "scale": self.scale,
            "name": self.name,
            "layer": self.layer,
            "filled": self.filled,
            "param_overrides": dict(self.param_overrides),
            "attach_to": self.attach_to,
            "attach_anchor": self.attach_anchor,
            "parent_anchor": self.parent_anchor,
            "fill_pattern": self.fill_pattern,
            "locked": self.locked,
            "role": role_to_str(self.role),
        }
        if self.attach_location is not None:
            data["attach_location"] = dict(self.attach_location)
        if self.parent_location is not None:
            data["parent_location"] = dict(self.parent_location)
        return data

    @classmethod
    def from_dict(cls, d: dict) -> "Component":
        raw_attach_anchor = d.get("attach_anchor", "")
        return cls(
            id=d.get("id"),
            asset_id=str(d.get("asset_id", "")),
            x=float(d.get("x", 0.0)),
            y=float(d.get("y", 0.0)),
            rotation=float(d.get("rotation", 0.0)),
            scale=float(d.get("scale", 1.0)),
            name=str(d.get("name", "")),
            layer=int(d.get("layer", 0)),
            filled=bool(d.get("filled", False)),
            param_overrides={
                str(k): float(v)
                for k, v in (d.get("param_overrides") or {}).items()
                if isinstance(v, (int, float))
            },
            attach_to=str(d.get("attach_to", "")),
            attach_anchor=(
                None
                if raw_attach_anchor is None
                else str(raw_attach_anchor)
            ),
            parent_anchor=str(d.get("parent_anchor", "")),
            fill_pattern=str(d.get("fill_pattern", "")),
            locked=bool(d.get("locked", False)),
            role=parse_role(d.get("role")),
            attach_location=d.get("attach_location"),
            parent_location=d.get("parent_location"),
        )
