"""
VectorContour — замкнутый контур из точек.

Чистые данные, без Qt. Координаты в МЕТРАХ.

node_ids — стабильные id для каждой точки. Позволяют semantic_groups
ссылаться на узлы, не завися от их индексов.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VectorContour:
    """Замкнутый контур. Список точек [(x, y), ...]."""

    points: list[tuple[float, float]] = field(default_factory=list)
    node_ids: list[str] = field(default_factory=list)
    closed: bool = True
    name: str = "Контур"

    def __post_init__(self):
        # Синхронизация: если есть точки, но нет node_ids — сгенерировать
        if self.points and not self.node_ids:
            self.node_ids = [
                f"n_{i:03d}" for i in range(len(self.points))
            ]
        # Если node_ids короче points — добить
        while len(self.node_ids) < len(self.points):
            self.node_ids.append(f"n_{len(self.node_ids):03d}")

    # ------------------------------------------------------------

    def add_point(
        self, x: float, y: float, node_id: str | None = None,
    ) -> int:
        idx = len(self.points)
        self.points.append((float(x), float(y)))
        if node_id is None:
            node_id = f"n_{idx:03d}"
        self.node_ids.append(node_id)
        return idx

    def insert_point(
        self, idx: int, x: float, y: float,
        node_id: str | None = None,
    ) -> int:
        """Вставить точку на позицию idx."""
        x = float(x)
        y = float(y)
        if node_id is None:
            node_id = f"n_{idx:03d}"
        self.points.insert(idx, (x, y))
        self.node_ids.insert(idx, node_id)
        return idx

    def set_point(self, idx: int, x: float, y: float) -> None:
        if 0 <= idx < len(self.points):
            self.points[idx] = (float(x), float(y))

    def get_point(self, idx: int) -> tuple[float, float] | None:
        if 0 <= idx < len(self.points):
            return self.points[idx]
        return None

    def remove_point(self, idx: int) -> None:
        """Удалить точку и её node_id."""
        if 0 <= idx < len(self.points):
            self.points.pop(idx)
        if 0 <= idx < len(self.node_ids):
            self.node_ids.pop(idx)

    def get_node_id(self, idx: int) -> str | None:
        if 0 <= idx < len(self.node_ids):
            return self.node_ids[idx]
        return None

    def count(self) -> int:
        return len(self.points)

    # ------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "closed": self.closed,
            "points": [[x, y] for (x, y) in self.points],
            "node_ids": list(self.node_ids),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VectorContour":
        pts = [(float(p[0]), float(p[1])) for p in d.get("points", [])]
        nids = list(d.get("node_ids", []))
        return cls(
            points=pts,
            node_ids=nids,
            closed=bool(d.get("closed", True)),
            name=d.get("name", "Контур"),
        )

    @classmethod
    def create_test_pentagon(
        cls, cx: float = 0.0, cy: float = 0.0, r: float = 3.0,
    ) -> "VectorContour":
        import math
        pts = []
        for i in range(5):
            angle = math.pi / 2 + i * 2 * math.pi / 5
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            pts.append((x, y))
        return cls(points=pts, closed=True, name="Пятиугольник")
