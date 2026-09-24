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
    ):
        self.count_x = max(1, int(count_x))
        self.count_y = max(1, int(count_y))
        self.spacing_x = max(0.0, float(spacing_x))
        self.spacing_y = max(0.0, float(spacing_y))

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
        return {
            "count_x": self.count_x,
            "count_y": self.count_y,
            "spacing_x": self.spacing_x,
            "spacing_y": self.spacing_y,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Distribution":
        if not isinstance(d, dict):
            d = {}
        return cls(
            count_x=d.get("count_x", 1),
            count_y=d.get("count_y", 1),
            spacing_x=d.get("spacing_x", 0.0),
            spacing_y=d.get("spacing_y", 0.0),
        )


class MountPoint:
    """Определение точки крепления в локальных координатах Asset."""

    def __init__(
        self,
        id: str | None = None,
        role: MountRole | str | None = None,
        position: tuple[float, float] = (0.0, 0.0),
        distribution: Distribution | None = None,
    ):
        self.id = id or self._generate_id()
        self.role: MountRole | None = parse_role(role)

        x, y = position
        self.position: tuple[float, float] = (float(x), float(y))

        self.distribution = (
            distribution if isinstance(distribution, Distribution)
            else Distribution()
        )

    @staticmethod
    def _generate_id() -> str:
        return "mp_" + uuid.uuid4().hex[:8]

    # ------------------------------------------------------------

    def resolve(self) -> list["MountLocation"]:
        """Развернуть MountPoint в список MountLocation.

        position - первая location. count_x=3 -> ровно 3 позиции.
        """
        result: list[MountLocation] = []
        x0, y0 = self.position
        sx = self.distribution.spacing_x
        sy = self.distribution.spacing_y

        for ix in range(self.distribution.count_x):
            for iy in range(self.distribution.count_y):
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

    def is_valid(self) -> bool:
        return bool(self.id)

    # ------------------------------------------------------------

    def to_dict(self) -> dict:
        from .mount_role import role_to_str
        return {
            "id": self.id,
            "role": role_to_str(self.role),
            "position": [self.position[0], self.position[1]],
            "distribution": self.distribution.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MountPoint":
        if not isinstance(d, dict):
            raise ValueError("MountPoint.from_dict: dict expected")

        pos_raw = d.get("position") or [0.0, 0.0]
        if not isinstance(pos_raw, (list, tuple)) or len(pos_raw) < 2:
            pos_raw = [0.0, 0.0]

        return cls(
            id=d.get("id"),
            role=parse_role(d.get("role")),
            position=(pos_raw[0], pos_raw[1]),
            distribution=Distribution.from_dict(
                d.get("distribution") or {}
            ),
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