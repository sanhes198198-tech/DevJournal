"""
VectorContour — замкнутый контур из точек.

Чистые данные, без Qt. Координаты в МЕТРАХ.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VectorContour:
    """Замкнутый контур. Список точек [(x, y), ...]."""

    points: list[tuple[float, float]] = field(default_factory=list)
    closed: bool = True
    name: str = "Контур"

    # ------------------------------------------------------------

    def add_point(self, x: float, y: float) -> int:
        self.points.append((float(x), float(y)))
        return len(self.points) - 1

    def set_point(self, idx: int, x: float, y: float) -> None:
        if 0 <= idx < len(self.points):
            self.points[idx] = (float(x), float(y))

    def get_point(self, idx: int) -> tuple[float, float] | None:
        if 0 <= idx < len(self.points):
            return self.points[idx]
        return None

    def count(self) -> int:
        return len(self.points)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "closed": self.closed,
            "points": [[x, y] for (x, y) in self.points],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VectorContour":
        pts = [(float(p[0]), float(p[1])) for p in d.get("points", [])]
        return cls(
            points=pts,
            closed=bool(d.get("closed", True)),
            name=d.get("name", "Контур"),
        )

    @classmethod
    def create_test_pentagon(cls, cx: float = 0.0, cy: float = 0.0, r: float = 3.0):
        """Тестовый пятиугольник в центре."""
        import math
        pts = []
        for i in range(5):
            angle = math.pi / 2 + i * 2 * math.pi / 5
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            pts.append((x, y))
        return cls(points=pts, closed=True, name="Пятиугольник")
