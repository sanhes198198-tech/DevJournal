"""
MountPoint + Distribution + MountLocation.

MountPoint - определение точки крепления в ЛОКАЛЬНЫХ координатах Asset.
Distribution - правило размножения (count_x/y, spacing_x/y).
MountLocation - вычисленная позиция (производная, НЕ сохраняется).
"""

from __future__ import annotations

import uuid

from .mount_role import MountRole, parse_role


class Distribution:
    """Как из одной MountPoint получить несколько MountLocation."""

    def __init__(
        self,
        count_x: int = 1,
        count_y: int = 1,
        spacing_x: float = 0.0,
        spacing_y: float = 0.0,
        margin_x: float = 0.0,
        margin_y: float = 0.0,
        adaptive_x: bool = False,
        adaptive_y: bool = False,
    ):
        self.count_x = max(1, int(count_x))
        self.count_y = max(1, int(count_y))
        self.spacing_x = max(0.0, float(spacing_x))
        self.spacing_y = max(0.0, float(spacing_y))
        # B3: margin — отступ от краёв bbox, метры.
        self.margin_x = max(0.0, float(margin_x))
        self.margin_y = max(0.0, float(margin_y))
        # B3: adaptive — если True, count вычисляется от размера bbox
        # с фиксированным spacing (окна добавляются при росте стены).
        self.adaptive_x = bool(adaptive_x)
        self.adaptive_y = bool(adaptive_y)

    def total_count(self) -> int:
        return self.count_x * self.count_y

    def is_simple(self) -> bool:
        """Простое распределение - одна точка, без размножения."""
        return (
            self.count_x == 1
            and self.count_y == 1
            and self.spacing_x == 0.0
            and self.spacing_y == 0.0
        )

    def to_dict(self) -> dict:
        d = {
            "count_x": self.count_x,
            "count_y": self.count_y,
            "spacing_x": self.spacing_x,
            "spacing_y": self.spacing_y,
        }
        # B3: новые поля пишем только если они не дефолтные.
        # Так старые JSON не распухают и backward compatible.
        if self.margin_x != 0.0:
            d["margin_x"] = self.margin_x
        if self.margin_y != 0.0:
            d["margin_y"] = self.margin_y
        if self.adaptive_x:
            d["adaptive_x"] = True
        if self.adaptive_y:
            d["adaptive_y"] = True
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Distribution":
        if not isinstance(d, dict):
            d = {}
        return cls(
            count_x=d.get("count_x", 1),
            count_y=d.get("count_y", 1),
            spacing_x=d.get("spacing_x", 0.0),
            spacing_y=d.get("spacing_y", 0.0),
            margin_x=d.get("margin_x", 0.0),
            margin_y=d.get("margin_y", 0.0),
            adaptive_x=d.get("adaptive_x", False),
            adaptive_y=d.get("adaptive_y", False),
        )


class MountPoint:
    """Определение точки крепления в локальных координатах Asset."""

    def __init__(
        self,
        id: str | None = None,
        role: MountRole | str | None = None,
        position: tuple[float, float] = (0.0, 0.0),
        distribution: Distribution | None = None,
        legacy_group_id: str | None = None,
        legacy_auto_rule: dict | None = None,
        anchor_mode: str = "absolute",
        anchor_x: float = 0.5,
        anchor_y: float = 0.5,
        semantic_group_id: str | None = None,
    ):
        self.id = id or self._generate_id()
        self.role: MountRole | None = parse_role(role)

        x, y = position
        self.position: tuple[float, float] = (float(x), float(y))

        self.distribution = (
            distribution if isinstance(distribution, Distribution)
            else Distribution()
        )

        # Поля для миграции из legacy (semantic_groups + auto_rule).
        # Если MountPoint создан вручную — None.
        self.legacy_group_id: str | None = (
            str(legacy_group_id) if legacy_group_id else None
        )
        self.legacy_auto_rule: dict | None = (
            dict(legacy_auto_rule) if legacy_auto_rule else None
        )

        # Explicit live binding used by group-bound endpoints. Keep this
        # separate from legacy_group_id, which is provenance from migration.
        self.semantic_group_id: str | None = (
            str(semantic_group_id) if semantic_group_id else None
        )

        # V22: Anchor mode — привязка к bbox контура.
        # "absolute"     — position в локальных координатах ассета (не едет)
        # "relative_xy"  — position вычисляется как xmin + ax*(xmax-xmin)
        self.anchor_mode: str = (
            str(anchor_mode) if anchor_mode else "absolute"
        )
        self.anchor_x: float = float(anchor_x)
        self.anchor_y: float = float(anchor_y)

    @staticmethod
    def _generate_id() -> str:
        return "mp_" + uuid.uuid4().hex[:8]

    # ------------------------------------------------------------

    def resolve(self, bbox=None) -> list["MountLocation"]:
        """V22 + V23: развернуть MountPoint в список MountLocation.

        V22: anchor_mode="relative_xy" -> x0/y0 считаются от bbox.
        V23: AUTO-FILL — если spacing=0 и count>1, шаг считается от bbox
             (равномерно от края до края стены).
        """
        if self.is_group_bound():
            raise ValueError(
                "Group-bound MountPoint requires Asset-aware resolution"
            )

        has_bbox = (
            self.anchor_mode == "relative_xy"
            and bbox is not None
            and len(bbox) == 4
        )

        if has_bbox:
            xmin, ymin, xmax, ymax = bbox
            sx = self.distribution.spacing_x
            sy = self.distribution.spacing_y
            cx = self.distribution.count_x
            cy = self.distribution.count_y

            # B3: adaptive_x — count от размера, spacing фиксирован
            if self.distribution.adaptive_x and sx > 0.0:
                margin = self.distribution.margin_x
                avail = (xmax - xmin) - 2.0 * margin
                if avail <= 0.0:
                    cx = 1
                    x0 = (xmin + xmax) / 2.0
                else:
                    cx = int(avail // sx) + 1
                    x0 = xmin + margin
            elif sx == 0.0 and cx > 1:
                sx = (xmax - xmin) / (cx - 1)
                x0 = xmin
            else:
                x0 = xmin + self.anchor_x * (xmax - xmin)

            # B3: adaptive_y
            if self.distribution.adaptive_y and sy > 0.0:
                margin = self.distribution.margin_y
                avail = (ymax - ymin) - 2.0 * margin
                if avail <= 0.0:
                    cy = 1
                    y0 = (ymin + ymax) / 2.0
                else:
                    cy = int(avail // sy) + 1
                    y0 = ymin + margin
            elif sy == 0.0 and cy > 1:
                sy = (ymax - ymin) / (cy - 1)
                y0 = ymin
            else:
                y0 = ymax - self.anchor_y * (ymax - ymin)
        else:
            x0, y0 = self.position
            sx = self.distribution.spacing_x
            sy = self.distribution.spacing_y
            cx = self.distribution.count_x
            cy = self.distribution.count_y

        result: list[MountLocation] = []
        for ix in range(cx):
            for iy in range(cy):
                px = x0 + ix * sx
                py = y0 + iy * sy
                result.append(
                    MountLocation(
                        mountpoint_id=self.id,
                        index_x=ix,
                        index_y=iy,
                        role=self.role,
                        position=(px, py),
                    )
                )
        return result

    def resolve_for_asset(
        self,
        asset,
        *,
        bbox=None,
        param_overrides: dict | None = None,
    ) -> list["MountLocation"]:
        """Resolve against an Asset when this point is group-bound.

        Static MountPoints keep the existing ``resolve(bbox)`` behavior.
        Group-bound points use the current SemanticGroup geometry, plus the
        supplied component parameter overrides, and produce one location.
        The returned position is Asset-local; the caller applies item
        centering and scene transforms separately.
        """
        if not self.is_group_bound():
            return self.resolve(bbox=bbox)

        if asset is None:
            raise ValueError("Group-bound MountPoint requires an Asset")
        if not self.distribution.is_simple():
            raise ValueError(
                "Group-bound MountPoint requires a single location"
            )

        centroid_resolver = getattr(
            asset, "semantic_group_centroid", None,
        )
        if not callable(centroid_resolver):
            raise ValueError(
                "Asset cannot resolve SemanticGroup positions"
            )
        position = centroid_resolver(
            self.semantic_group_id,
            param_overrides=param_overrides,
        )
        if position is None:
            raise ValueError(
                f"Unknown or empty SemanticGroup: "
                f"{self.semantic_group_id!r}"
            )

        return [
            MountLocation(
                mountpoint_id=self.id,
                index_x=0,
                index_y=0,
                role=self.role,
                position=position,
            ),
        ]

    def is_valid(self) -> bool:
        return bool(self.id)

    def is_group_bound(self) -> bool:
        """Whether this point is bound to a live SemanticGroup."""
        return self.semantic_group_id is not None

    # ------------------------------------------------------------

    def to_dict(self) -> dict:
        from .mount_role import role_to_str
        d = {
            "id": self.id,
            "role": role_to_str(self.role),
            "position": [self.position[0], self.position[1]],
            "distribution": self.distribution.to_dict(),
        }
        if self.anchor_mode != "absolute":
            d["anchor_mode"] = self.anchor_mode
            d["anchor_x"] = self.anchor_x
            d["anchor_y"] = self.anchor_y
        if self.legacy_group_id is not None:
            d["legacy_group_id"] = self.legacy_group_id
        if self.legacy_auto_rule is not None:
            d["legacy_auto_rule"] = dict(self.legacy_auto_rule)
        if self.semantic_group_id is not None:
            d["semantic_group_id"] = self.semantic_group_id
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "MountPoint":
        if not isinstance(d, dict):
            raise ValueError("MountPoint.from_dict: dict expected")

        pos_raw = d.get("position") or [0.0, 0.0]
        if not isinstance(pos_raw, (list, tuple)) or len(pos_raw) < 2:
            pos_raw = [0.0, 0.0]

        legacy_ar = d.get("legacy_auto_rule")
        if legacy_ar is not None and not isinstance(legacy_ar, dict):
            legacy_ar = None

        return cls(
            id=d.get("id"),
            role=parse_role(d.get("role")),
            position=(pos_raw[0], pos_raw[1]),
            distribution=Distribution.from_dict(
                d.get("distribution") or {}
            ),
            legacy_group_id=d.get("legacy_group_id"),
            legacy_auto_rule=legacy_ar,
            anchor_mode=str(d.get("anchor_mode", "absolute")),
            anchor_x=float(d.get("anchor_x", 0.5)),
            anchor_y=float(d.get("anchor_y", 0.5)),
            semantic_group_id=d.get("semantic_group_id"),
        )


class MountLocation:
    """Вычисленная позиция для крепления. НЕ сохраняется в Asset.

    Адресуется парой (mountpoint_id, index_x, index_y).
    """

    __slots__ = (
        "mountpoint_id", "index_x", "index_y",
        "role", "position",
    )

    def __init__(
        self,
        mountpoint_id: str,
        index_x: int,
        index_y: int,
        role: MountRole | None,
        position: tuple[float, float],
    ):
        self.mountpoint_id = str(mountpoint_id)
        self.index_x = int(index_x)
        self.index_y = int(index_y)
        self.role: MountRole | None = role
        self.position: tuple[float, float] = (
            float(position[0]),
            float(position[1]),
        )

    def address(self) -> tuple[str, int, int]:
        """Уникальный адрес в системе."""
        return (self.mountpoint_id, self.index_x, self.index_y)

    def __repr__(self) -> str:
        return (
            f"MountLocation({self.mountpoint_id}"
            f"[{self.index_x},{self.index_y}] "
            f"role={self.role} pos={self.position})"
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, MountLocation):
            return NotImplemented
        return self.address() == other.address()
