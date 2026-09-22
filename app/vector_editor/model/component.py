"""
Component — ссылка на другой Asset внутри составного Asset'а.

Пример: башня состоит из [стена, купол, окно_1, окно_2].
Каждый — Component: ссылка на asset_id + позиция/поворот/масштаб.

Модель чистая, без Qt.
"""

from __future__ import annotations

import uuid


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
        attach_anchor: str = "",
        parent_anchor: str = "",
        slot_policy: dict | None = None,
        fill_pattern: str = "",
        locked: bool = False,
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
        # V11: привязка через anchors
        # attach_to — id родителя в композите
        # attach_anchor — наш якорь (anchor_bottom)
        # parent_anchor — якорь родителя (anchor_top)
        self.attach_to: str = str(attach_to or "")
        self.attach_anchor: str = str(attach_anchor or "")
        self.parent_anchor: str = str(parent_anchor or "")
        # V11: политика управления видимостью дочерних
        # компонентов на слотах. None = выключено.
        # {"enabled": bool, "clearance": float}
        self.slot_policy: dict | None = (
            dict(slot_policy) if slot_policy else None
        )
        # V11: текстура заливки. "" = без текстуры.
        # "hatch" = серая диагональная штриховка.
        # "diamonds" = ромбы (косой крест).
        self.fill_pattern: str = str(fill_pattern or "")
        # V12: блокировка перемещения и параметров.
        # Заблокированный можно выделить и удалить, но нельзя
        # двигать (drag) и менять height/width через панель.
        self.locked: bool = bool(locked)

    @staticmethod
    def _generate_id() -> str:
        return "c_" + uuid.uuid4().hex[:8]

    # ------------------------------------------------------------

    def is_valid(self) -> bool:
        """Базовая валидация: есть ссылка на asset."""
        return bool(self.asset_id)

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
        attach_anchor: str, parent_anchor: str,
    ) -> None:
        """Прикрепить этот компонент к родителю."""
        self.attach_to = str(parent_id)
        self.attach_anchor = str(attach_anchor)
        self.parent_anchor = str(parent_anchor)

    def clear_attachment(self) -> None:
        self.attach_to = ""
        self.attach_anchor = ""
        self.parent_anchor = ""

    def is_attached(self) -> bool:
        return bool(
            self.attach_to
            and self.attach_anchor
            and self.parent_anchor
        )

    def to_dict(self) -> dict:
        return {
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
            "slot_policy": self.slot_policy,
            "fill_pattern": self.fill_pattern,
            "locked": self.locked,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Component":
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
            attach_anchor=str(d.get("attach_anchor", "")),
            parent_anchor=str(d.get("parent_anchor", "")),
            slot_policy=d.get("slot_policy"),
            fill_pattern=str(d.get("fill_pattern", "")),
            locked=bool(d.get("locked", False)),
        )
