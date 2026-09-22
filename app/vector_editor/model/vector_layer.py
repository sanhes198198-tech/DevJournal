"""
VectorLayer — один слой (контур) внутри Asset'а.

Ассет может содержать несколько слоёв: основная форма,
декор, зубцы, окна и т.д. Каждый слой — независимый контур
со своими точками, рёбрами и extra-элементами.

V16: этап 1 — только модель. Asset.geometry остаётся для
обратной совместимости, layers заполняется автоматически
при загрузке старого JSON (один слой из geometry).
"""
from __future__ import annotations

import uuid


class VectorLayer:
    """Один слой контура внутри Asset'а."""

    def __init__(
        self,
        id: str | None = None,
        name: str = "Слой",
        visible: bool = True,
        locked: bool = False,
        color: str = "#1A1A1A",
        geometry: dict | None = None,
        fillable: bool = True,
    ):
        self.id = id or self._generate_id()
        self.name = name
        self.visible = bool(visible)
        self.locked = bool(locked)
        self.color = str(color or "#1A1A1A")
        # V16: слой заливается текстурой (fill_pattern) или
        # остаётся только контуром. Рама поверх окна — fillable=False.
        self.fillable = bool(fillable)
        # geometry — dict той же структуры что и Asset.geometry
        # (contour, node_ids, groups, extra_points, extra_node_ids,
        #  extra_edges, arcs, closed, units)
        self.geometry = geometry or self._empty_geometry()

    @staticmethod
    def _generate_id() -> str:
        return "L_" + uuid.uuid4().hex[:8]

    @staticmethod
    def _empty_geometry() -> dict:
        return {
            "contour": [],
            "closed": True,
            "units": "m",
            "node_ids": [],
            "groups": {},
            "extra_edges": [],
            "arcs": [],
            "extra_points": [],
            "extra_node_ids": [],
        }

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "visible": self.visible,
            "locked": self.locked,
            "color": self.color,
            "fillable": self.fillable,
            "geometry": self.geometry,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VectorLayer":
        return cls(
            id=d.get("id"),
            name=d.get("name", "Слой"),
            visible=bool(d.get("visible", True)),
            locked=bool(d.get("locked", False)),
            color=str(d.get("color", "#1A1A1A")),
            fillable=bool(d.get("fillable", True)),
            geometry=d.get("geometry") or cls._empty_geometry(),
        )