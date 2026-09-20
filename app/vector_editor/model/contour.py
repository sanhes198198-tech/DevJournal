"""
VectorContour — замкнутый/разомкнутый контур из точек.

Чистые данные, без Qt. Координаты в МЕТРАХ.

node_ids — стабильные id для каждой точки. Позволяют semantic_groups
и extra_edges ссылаться на узлы, не завися от их индексов.

V8-lite: extra_edges — дополнительные рёбра между НЕсоседними узлами.
Хранятся как пары node_ids (строки), не индексы. Это делает их
устойчивыми к удалению / вставке / сдвигу точек.

Пример: extra_edges = [("n_003", "n_007")]
→ рисуется основное кольцо + дополнительная линия n_003—n_007.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VectorContour:
    """Контур. points + node_ids + опциональные extra_edges."""

    points: list[tuple[float, float]] = field(default_factory=list)
    node_ids: list[str] = field(default_factory=list)
    closed: bool = True
    name: str = "Контур"
    # Пары node_ids (не индексов!)
    extra_edges: list[tuple[str, str]] = field(default_factory=list)

    def __post_init__(self):
        if self.points and not self.node_ids:
            self.node_ids = [
                f"n_{i:03d}" for i in range(len(self.points))
            ]
        while len(self.node_ids) < len(self.points):
            self.node_ids.append(f"n_{len(self.node_ids):03d}")

    # ------------------------------------------------------------
    # POINTS
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
        """Удалить точку, её node_id и связанные extra_edges.

        Все extra_edges, в которых встречается удаляемый node_id,
        тоже удаляются (каскадно). Остальные extra_edges остаются
        как есть — они ссылаются на node_ids, а не на индексы.
        """
        if not (0 <= idx < len(self.points)):
            return

        removed_id = (
            self.node_ids[idx] if idx < len(self.node_ids) else None
        )

        self.points.pop(idx)
        if idx < len(self.node_ids):
            self.node_ids.pop(idx)

        if removed_id is not None:
            self.extra_edges = [
                (a, b)
                for (a, b) in self.extra_edges
                if a != removed_id and b != removed_id
            ]

    def get_node_id(self, idx: int) -> str | None:
        if 0 <= idx < len(self.node_ids):
            return self.node_ids[idx]
        return None

    def index_of(self, node_id: str) -> int:
        """Индекс узла по node_id, или -1, если не найден."""
        try:
            return self.node_ids.index(node_id)
        except ValueError:
            return -1

    def _next_node_id(self) -> str:
        """Следующий свободный n_NNN."""
        max_n = -1
        for nid in self.node_ids:
            if nid.startswith("n_") and nid[2:].isdigit():
                max_n = max(max_n, int(nid[2:]))
        return f"n_{max_n + 1:03d}"

    def insert_point_after(
        self,
        idx: int,
        x: float,
        y: float,
        node_id: str | None = None,
    ) -> str | None:
        """Вставить точку СРАЗУ ПОСЛЕ узла idx.
        Возвращает node_id нового узла или None.
        """
        if idx < 0 or idx >= len(self.points):
            return None

        if node_id is None:
            node_id = self._next_node_id()

        insert_at = idx + 1
        self.points.insert(insert_at, (float(x), float(y)))
        self.node_ids.insert(insert_at, node_id)
        return node_id

    def count(self) -> int:
        return len(self.points)

    # ------------------------------------------------------------
    # EXTRA EDGES
    # ------------------------------------------------------------

    def has_extra_edge(self, a_id: str, b_id: str) -> bool:
        """Есть ли extra-ребро между a_id и b_id (порядок не важен)."""
        key = frozenset((a_id, b_id))
        return any(
            frozenset(edge) == key
            for edge in self.extra_edges
        )

    def add_extra_edge(self, a_id: str, b_id: str) -> bool:
        """Добавить extra-ребро. True при успехе."""
        if not a_id or not b_id:
            return False
        if a_id == b_id:
            return False
        if a_id not in self.node_ids or b_id not in self.node_ids:
            return False
        if self.has_extra_edge(a_id, b_id):
            return False

        self.extra_edges.append((a_id, b_id))
        return True

    def remove_extra_edge(self, a_id: str, b_id: str) -> bool:
        """Удалить extra-ребро. True если было удалено."""
        key = frozenset((a_id, b_id))
        for i, edge in enumerate(self.extra_edges):
            if frozenset(edge) == key:
                self.extra_edges.pop(i)
                return True
        return False

    # ------------------------------------------------------------
    # СЕРИАЛИЗАЦИЯ
    # ------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "closed": self.closed,
            "points": [[x, y] for (x, y) in self.points],
            "node_ids": list(self.node_ids),
            "extra_edges": [
                [a, b] for (a, b) in self.extra_edges
            ],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VectorContour":
        pts = [
            (float(p[0]), float(p[1]))
            for p in d.get("points", [])
        ]

        nids = list(d.get("node_ids", []))

        # Если node_ids короче points — добить уникальными id
        if len(nids) < len(pts):
            used = set(nids)
            next_index = len(nids)
            while len(nids) < len(pts):
                candidate = f"n_{next_index:03d}"
                next_index += 1
                if candidate in used:
                    continue
                nids.append(candidate)
                used.add(candidate)

        valid_ids = set(nids)

        raw_edges = d.get("extra_edges") or []
        extra_edges: list[tuple[str, str]] = []

        for raw in raw_edges:
            if not isinstance(raw, (list, tuple)):
                continue
            if len(raw) != 2:
                continue

            a, b = raw

            # Backward compat: старый формат хранил индексы
            if isinstance(a, int) and 0 <= a < len(nids):
                a = nids[a]
            if isinstance(b, int) and 0 <= b < len(nids):
                b = nids[b]

            if not isinstance(a, str) or not isinstance(b, str):
                continue
            if a == b:
                continue
            if a not in valid_ids or b not in valid_ids:
                continue

            # Отбрасываем дубликаты
            if any(
                frozenset(edge) == frozenset((a, b))
                for edge in extra_edges
            ):
                continue

            extra_edges.append((a, b))

        return cls(
            points=pts,
            node_ids=nids,
            closed=bool(d.get("closed", True)),
            name=d.get("name", "Контур"),
            extra_edges=extra_edges,
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
