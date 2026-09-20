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
    # Extra-only узлы (не входят в main-контур).
    # Живут отдельно, main не трогают. id с префиксом "e_".
    extra_points: list[tuple[float, float]] = field(default_factory=list)
    extra_node_ids: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.points and not self.node_ids:
            self.node_ids = [
                f"n_{i:03d}" for i in range(len(self.points))
            ]
        while len(self.node_ids) < len(self.points):
            self.node_ids.append(f"n_{len(self.node_ids):03d}")

        # То же для extra-точек
        while len(self.extra_node_ids) < len(self.extra_points):
            self.extra_node_ids.append(
                f"e_{len(self.extra_node_ids):03d}"
            )

    # ------------------------------------------------------------
    # POINTS
    # ------------------------------------------------------------

    def add_point(
        self, x: float, y: float, node_id: str | None = None,
    ) -> int:
        idx = len(self.points)
        self.points.append((float(x), float(y)))
        if node_id is None:
            node_id = self._next_node_id()
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
            node_id = self._next_node_id()
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
        """Следующий свободный n_NNN.

        Учитывает и main, и extra — чтобы не создать id,
        который уже занят.
        """
        all_ids = set(self.node_ids) | set(self.extra_node_ids)
        max_n = -1
        for nid in all_ids:
            if nid.startswith("n_") and nid[2:].isdigit():
                max_n = max(max_n, int(nid[2:]))
        # Дополнительная защита: если по какой-то причине
        # max_n + 1 уже занят — сдвигаем дальше
        candidate = f"n_{max_n + 1:03d}"
        while candidate in all_ids:
            max_n += 1
            candidate = f"n_{max_n + 1:03d}"
        return candidate

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

    def sanitize(self) -> int:
        """Починить контур: убрать дубли node_ids, битые extra_edges.

        Возвращает количество исправлений.
        """
        fixes = 0

        # 1. Дедупликация main node_ids
        # Собираем множество ВСЕХ используемых id (main + extra),
        # чтобы при генерации не столкнуться ни с чем
        all_used: set[str] = set(self.node_ids) | set(self.extra_node_ids)

        seen: set[str] = set()
        new_main_ids: list[str] = []
        for nid in self.node_ids:
            if nid in seen:
                # Генерируем уникальный id, не совпадающий ни с чем
                max_n = -1
                for existing in all_used:
                    if (existing.startswith("n_")
                            and existing[2:].isdigit()):
                        max_n = max(max_n, int(existing[2:]))
                candidate = f"n_{max_n + 1:03d}"
                while candidate in all_used:
                    max_n += 1
                    candidate = f"n_{max_n + 1:03d}"
                nid = candidate
                all_used.add(candidate)
                fixes += 1
            seen.add(nid)
            new_main_ids.append(nid)
        self.node_ids = new_main_ids

        # 2. Дедупликация extra_node_ids
        seen_e: set[str] = set()
        new_extra_ids: list[str] = []
        for nid in self.extra_node_ids:
            if nid in seen_e or nid in seen:
                new_nid = f"e_{len(new_extra_ids):03d}"
                while new_nid in seen_e or new_nid in seen:
                    new_nid = f"e_{len(new_extra_ids):03d}_x"
                nid = new_nid
                fixes += 1
            seen_e.add(nid)
            new_extra_ids.append(nid)
        self.extra_node_ids = new_extra_ids

        # 2b. Выровнять длины extra_points / extra_node_ids
        # (если рассинхрон — обрезаем до короткого)
        if len(self.extra_points) != len(self.extra_node_ids):
            n = min(
                len(self.extra_points),
                len(self.extra_node_ids),
            )
            fixes += (
                abs(len(self.extra_points) - len(self.extra_node_ids))
            )
            self.extra_points = self.extra_points[:n]
            self.extra_node_ids = self.extra_node_ids[:n]

        # 3. Отбросить битые extra_edges
        all_ids = set(self.node_ids) | set(self.extra_node_ids)
        new_edges: list[tuple[str, str]] = []
        seen_edges: set[frozenset] = set()
        for a, b in self.extra_edges:
            if a not in all_ids or b not in all_ids or a == b:
                fixes += 1
                continue
            key = frozenset((a, b))
            if key in seen_edges:
                fixes += 1
                continue
            seen_edges.add(key)
            new_edges.append((a, b))
        self.extra_edges = new_edges

        # 4. Убрать висящие extra_points (без edges)
        used_extra: set[str] = set()
        for a, b in self.extra_edges:
            used_extra.add(a)
            used_extra.add(b)

        if used_extra:
            keep_pts: list[tuple[float, float]] = []
            keep_ids: list[str] = []
            for i, nid in enumerate(self.extra_node_ids):
                if nid in used_extra:
                    keep_pts.append(self.extra_points[i])
                    keep_ids.append(nid)
            if len(keep_ids) != len(self.extra_node_ids):
                fixes += len(self.extra_node_ids) - len(keep_ids)
                self.extra_points = keep_pts
                self.extra_node_ids = keep_ids

        return fixes

    def validate(self) -> list[str]:
        """Проверить инварианты. Возвращает список проблем."""
        problems: list[str] = []

        # 1. points ↔ node_ids
        if len(self.points) != len(self.node_ids):
            problems.append(
                f"points={len(self.points)} "
                f"node_ids={len(self.node_ids)} — разная длина"
            )

        # 2. extra_points ↔ extra_node_ids
        if len(self.extra_points) != len(self.extra_node_ids):
            problems.append(
                f"extra_points={len(self.extra_points)} "
                f"extra_node_ids={len(self.extra_node_ids)}"
            )

        # 3. Уникальность node_ids
        main_set = set(self.node_ids)
        if len(main_set) != len(self.node_ids):
            problems.append(
                f"дубли в main node_ids "
                f"({len(self.node_ids)} шт, "
                f"{len(main_set)} уник)"
            )

        extra_set = set(self.extra_node_ids)
        if len(extra_set) != len(self.extra_node_ids):
            problems.append(
                f"дубли в extra_node_ids "
                f"({len(self.extra_node_ids)} шт, "
                f"{len(extra_set)} уник)"
            )

        # 4. Пересечение main и extra id
        overlap = main_set & extra_set
        if overlap:
            problems.append(
                f"id пересекаются main/extra: {overlap}"
            )

        # 5. Extra_edges — все ссылки валидны
        all_ids = main_set | extra_set
        for i, (a, b) in enumerate(self.extra_edges):
            if a not in all_ids:
                problems.append(
                    f"extra_edges[{i}]=({a},{b}): "
                    f"id {a!r} не существует"
                )
            if b not in all_ids:
                problems.append(
                    f"extra_edges[{i}]=({a},{b}): "
                    f"id {b!r} не существует"
                )
            if a == b:
                problems.append(
                    f"extra_edges[{i}] самоссылка ({a})"
                )

        # 6. Индексы в extra_edges не дублируются
        seen: set[frozenset] = set()
        for i, (a, b) in enumerate(self.extra_edges):
            key = frozenset((a, b))
            if key in seen:
                problems.append(
                    f"extra_edges[{i}]=({a},{b}) дубликат"
                )
            seen.add(key)

        return problems

    def snapshot(self) -> dict:
        """Полный снимок состояния контура для undo."""
        return {
            "points": list(self.points),
            "node_ids": list(self.node_ids),
            "extra_edges": list(self.extra_edges),
            "extra_points": list(self.extra_points),
            "extra_node_ids": list(self.extra_node_ids),
        }

    def restore(self, snap: dict) -> None:
        """Восстановить состояние из snapshot()."""
        self.points = list(snap.get("points", []))
        self.node_ids = list(snap.get("node_ids", []))
        self.extra_edges = list(snap.get("extra_edges", []))
        self.extra_points = list(snap.get("extra_points", []))
        self.extra_node_ids = list(
            snap.get("extra_node_ids", [])
        )

    def count(self) -> int:
        return len(self.points)

    def extra_count(self) -> int:
        return len(self.extra_points)

    # ------------------------------------------------------------
    # EXTRA-ONLY NODES (не входят в main-контур)
    # ------------------------------------------------------------

    def has_node(self, node_id: str) -> bool:
        """True, если node_id есть в main или в extra-списке."""
        return (
            node_id in self.node_ids
            or node_id in self.extra_node_ids
        )

    def is_extra_node(self, node_id: str) -> bool:
        return node_id in self.extra_node_ids

    def _next_extra_node_id(self) -> str:
        max_n = -1
        for nid in self.extra_node_ids:
            if nid.startswith("e_") and nid[2:].isdigit():
                max_n = max(max_n, int(nid[2:]))
        return f"e_{max_n + 1:03d}"

    def add_extra_point(
        self, x: float, y: float, node_id: str | None = None,
    ) -> str:
        """Добавить extra-only узел. Возвращает его node_id."""
        if node_id is None:
            node_id = self._next_extra_node_id()
        self.extra_points.append((float(x), float(y)))
        self.extra_node_ids.append(node_id)
        return node_id

    def remove_extra_point(self, node_id: str) -> bool:
        """Удалить extra-узел + все extra_edges с ним."""
        if node_id not in self.extra_node_ids:
            return False

        i = self.extra_node_ids.index(node_id)
        self.extra_points.pop(i)
        self.extra_node_ids.pop(i)

        self.extra_edges = [
            (a, b)
            for (a, b) in self.extra_edges
            if a != node_id and b != node_id
        ]
        return True

    def get_point_by_id(
        self, node_id: str,
    ) -> tuple[float, float] | None:
        """Координаты узла из main или extra списка."""
        if node_id in self.node_ids:
            return self.points[self.node_ids.index(node_id)]
        if node_id in self.extra_node_ids:
            return self.extra_points[
                self.extra_node_ids.index(node_id)
            ]
        return None

    def set_point_by_id(
        self, node_id: str, x: float, y: float,
    ) -> bool:
        """Обновить координаты узла (main или extra)."""
        if node_id in self.node_ids:
            i = self.node_ids.index(node_id)
            self.points[i] = (float(x), float(y))
            return True
        if node_id in self.extra_node_ids:
            i = self.extra_node_ids.index(node_id)
            self.extra_points[i] = (float(x), float(y))
            return True
        return False

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
        """Добавить extra-ребро. True при успехе.

        Узлы могут быть как main (n_*), так и extra (e_*).
        """
        if not a_id or not b_id:
            return False
        if a_id == b_id:
            return False
        if not self.has_node(a_id) or not self.has_node(b_id):
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
            "extra_points": [
                [x, y] for (x, y) in self.extra_points
            ],
            "extra_node_ids": list(self.extra_node_ids),
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

        # Extra-only точки парсим ДО валидации edges,
        # чтобы ссылки на e_* не отбрасывались.
        raw_extra_pts = d.get("extra_points") or []
        extra_pts = [
            (float(p[0]), float(p[1]))
            for p in raw_extra_pts
            if isinstance(p, (list, tuple)) and len(p) >= 2
        ]
        extra_nids = list(d.get("extra_node_ids", []))

        # Синхронизируем длины (если JSON сломан)
        while len(extra_nids) < len(extra_pts):
            extra_nids.append(f"e_{len(extra_nids):03d}")

        valid_ids = set(nids) | set(extra_nids)

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
            extra_points=extra_pts,
            extra_node_ids=extra_nids,
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
