"""
Asset — параметризованный архитектурный объект.

Надстройка над VectorContour: контур остаётся чистой геометрией,
а Asset добавляет метаданные (имя, тип, группы, параметры, правила).

V3: только создание, сериализация. Без UI параметров и генерации.
"""

from __future__ import annotations

import uuid
from typing import Any

from .contour import VectorContour
from .semantic_group import SemanticGroup
from .parameter import Parameter
from .reference_image import ReferenceImage


# ============================================================
# ТИПЫ ASSET (категории назначения)
# ============================================================

ASSET_TYPES: tuple[tuple[str, str], ...] = (
    ("tower_body", "Башня — тело"),
    ("tower_tier", "Башня — ярус"),
    ("roof", "Крыша"),
    ("dome", "Купол"),
    ("window", "Окно"),
    ("door", "Дверь"),
    ("wall_section", "Участок стены"),
    ("foundation", "Основание"),
    ("ornament", "Декор"),
    ("other", "Прочее"),
)

ASSET_TYPE_IDS: tuple[str, ...] = tuple(t[0] for t in ASSET_TYPES)


# ============================================================
# ASSET
# ============================================================

class Asset:
    """Параметризованный архитектурный ассет."""

    def __init__(
        self,
        asset_id: str | None = None,
        name: str = "Новый ассет",
        type_: str = "other",
        geometry: dict | None = None,
        semantic_groups: dict | None = None,
        parameters: dict | None = None,
        generation_rules: dict | None = None,
    ):
        self.id = asset_id or self._generate_id()
        self.name = name
        self.type = type_ if type_ in ASSET_TYPE_IDS else "other"
        self.geometry = geometry or self._empty_geometry()
        self.semantic_groups: dict[str, SemanticGroup] = semantic_groups or {}
        self.parameters = parameters or {}
        self.reference_image: ReferenceImage | None = None
        self.generation_rules = generation_rules or self._default_rules()

    # ------------------------------------------------------------
    # ФАБРИКИ
    # ------------------------------------------------------------

    @staticmethod
    def _generate_id() -> str:
        return uuid.uuid4().hex[:12]

    @staticmethod
    def _empty_geometry() -> dict:
        return {
            "contour": [],
            "closed": True,
            "units": "m",
            "node_ids": [],
            "groups": {},
            "extra_edges": [],
            "extra_points": [],
            "extra_node_ids": [],
        }

    @staticmethod
    def _default_rules() -> dict:
        return {
            "allow_width_variation": False,
            "allow_height_variation": False,
            "irregularity": 0.0,
            "repeatable": False,
        }

    @classmethod
    def from_contour(
        cls,
        contour: VectorContour,
        name: str = "Новый ассет",
        type_: str = "other",
        asset_id: str | None = None,
    ) -> "Asset":
        """Создать Asset из существующего VectorContour.

        Автоматически создаёт node_ids и технические группы рёбер.
        asset_id — если передан, сохраняется (для Save поверх).
        """
        points = list(contour.points)
        n = len(points)

        # Используем node_ids из контура, если они есть и совпадают
        # по длине. Иначе — генерируем заново.
        node_ids = list(contour.node_ids)
        if len(node_ids) != n:
            node_ids = [f"n_{i:03d}" for i in range(n)]

        groups: dict[str, list[str]] = {}
        if n >= 2:
            segments = range(n) if contour.closed else range(n - 1)
            for i in segments:
                a = node_ids[i]
                b = node_ids[(i + 1) % n]
                groups[f"edge_{i:03d}"] = [a, b]

        # Extra-узлы и extra-edges сохраняются как есть (они
        # ссылаются на node_ids из main или extra).
        extra_points = list(getattr(contour, "extra_points", []))
        extra_node_ids = list(
            getattr(contour, "extra_node_ids", [])
        )

        # Синхронизация (на всякий случай)
        while len(extra_node_ids) < len(extra_points):
            extra_node_ids.append(
                f"e_{len(extra_node_ids):03d}"
            )

        valid_all_ids = set(node_ids) | set(extra_node_ids)

        geometry = {
            "contour": [[float(x), float(y)] for (x, y) in points],
            "closed": bool(contour.closed),
            "units": "m",
            "node_ids": node_ids,
            "groups": groups,
            "extra_edges": [
                [a, b]
                for (a, b) in getattr(contour, "extra_edges", [])
                if a in valid_all_ids and b in valid_all_ids
            ],
            "extra_points": [
                [float(x), float(y)] for (x, y) in extra_points
            ],
            "extra_node_ids": extra_node_ids,
        }

        return cls(
            asset_id=asset_id,
            name=name,
            type_=type_,
            geometry=geometry,
        )

    # ------------------------------------------------------------
    # СЕРИАЛИЗАЦИЯ
    # ------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "geometry": self.geometry,
            "semantic_groups": {
                gid: g.to_dict()
                for gid, g in self.semantic_groups.items()
            },
            "parameters": {
                pid: p.to_dict()
                for pid, p in self.parameters.items()
            },
            "reference_image": (
                self.reference_image.to_dict()
                if self.reference_image is not None
                else None
            ),
            "generation_rules": self.generation_rules,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Asset":
        groups_raw = d.get("semantic_groups") or {}
        groups: dict[str, SemanticGroup] = {}
        for gid, gdict in groups_raw.items():
            try:
                groups[gid] = SemanticGroup.from_dict(gdict)
            except Exception:
                continue

        params_raw = d.get("parameters") or {}
        params: dict[str, Parameter] = {}
        if isinstance(params_raw, dict):
            for pid, pdict in params_raw.items():
                if not isinstance(pdict, dict):
                    continue
                try:
                    params[pid] = Parameter.from_dict(pdict)
                except Exception:
                    continue

        ref_raw = d.get("reference_image")
        ref: ReferenceImage | None = None
        if isinstance(ref_raw, dict):
            try:
                ref = ReferenceImage.from_dict(ref_raw)
            except Exception:
                ref = None

        asset = cls(
            asset_id=d.get("id"),
            name=d.get("name", "Новый ассет"),
            type_=d.get("type", "other"),
            geometry=d.get("geometry") or cls._empty_geometry(),
            semantic_groups=groups,
            parameters=params,
            generation_rules=d.get("generation_rules") or cls._default_rules(),
        )
        asset.reference_image = ref
        return asset

    # ------------------------------------------------------------
    # ДОСТУП
    # ------------------------------------------------------------

    def points(self) -> list[tuple[float, float]]:
        return [(float(p[0]), float(p[1])) for p in self.geometry.get("contour", [])]

    def is_closed(self) -> bool:
        return bool(self.geometry.get("closed", True))

    def node_count(self) -> int:
        return len(self.geometry.get("node_ids", []))

    def group_count(self) -> int:
        return len(self.geometry.get("groups", {}))

    # ------------------------------------------------------------
    # EXTRA EDGES
    # ------------------------------------------------------------

    def extra_edges(self) -> list[tuple[str, str]]:
        """Вернуть extra_edges, нормализовав старый index-формат.

        - int-индексы превращаются в node_ids по node_ids-списку
        - отбрасываются пары с несуществующими id
        - отбрасываются self-пары
        - отбрасываются дубликаты

        После вызова `geometry["extra_edges"]` перезаписывается
        нормализованным списком.
        """
        node_ids = list(self.geometry.get("node_ids", []))
        extra_ids = list(self.geometry.get("extra_node_ids", []))
        valid = set(node_ids) | set(extra_ids)

        # Склеенный список для backward compat int → node_id.
        # Порядок: сначала main, потом extra — соответствует
        # порядку, в котором когда-то могли идти индексы.
        all_ids = node_ids + extra_ids

        result: list[tuple[str, str]] = []

        for raw in self.geometry.get("extra_edges", []) or []:
            if not isinstance(raw, (list, tuple)):
                continue
            if len(raw) != 2:
                continue

            a, b = raw

            if isinstance(a, int) and 0 <= a < len(all_ids):
                a = all_ids[a]
            if isinstance(b, int) and 0 <= b < len(all_ids):
                b = all_ids[b]

            if not isinstance(a, str) or not isinstance(b, str):
                continue
            if a == b:
                continue
            if a not in valid or b not in valid:
                continue

            if any(
                frozenset(edge) == frozenset((a, b))
                for edge in result
            ):
                continue

            result.append((a, b))

        # Нормализуем geometry сразу
        self.geometry["extra_edges"] = [
            [a, b] for a, b in result
        ]

        return result

    # ------------------------------------------------------------
    # SEMANTIC GROUPS
    # ------------------------------------------------------------

    def add_semantic_group(self, group: SemanticGroup) -> None:
        self.semantic_groups[group.id] = group

    def remove_semantic_group(self, group_id: str) -> SemanticGroup | None:
        return self.semantic_groups.pop(group_id, None)

    def get_semantic_group(self, group_id: str) -> SemanticGroup | None:
        return self.semantic_groups.get(group_id)

    def find_groups_by_node(self, node_id: str) -> list[SemanticGroup]:
        """Все группы, содержащие данный узел."""
        return [
            g for g in self.semantic_groups.values()
            if g.contains(node_id)
        ]

    def get_group_edges(self, group_id: str) -> list[str]:
        """id рёбер, оба конца которых лежат в группе.

        Использует geometry.groups (edge_xxx → [n_a, n_b]).
        """
        group = self.semantic_groups.get(group_id)
        if group is None:
            return []

        edges_map = self.geometry.get("groups", {})
        result = []
        for edge_id, edge_nodes in edges_map.items():
            if len(edge_nodes) != 2:
                continue
            a, b = edge_nodes
            if group.contains(a) and group.contains(b):
                result.append(edge_id)
        return result

    def semantic_group_count(self) -> int:
        return len(self.semantic_groups)

    # ------------------------------------------------------------
    # PARAMETERS
    # ------------------------------------------------------------

    def add_parameter(self, param: Parameter) -> None:
        self.parameters[param.id] = param

    def remove_parameter(self, param_id: str) -> Parameter | None:
        return self.parameters.pop(param_id, None)

    def get_parameter(self, param_id: str) -> Parameter | None:
        return self.parameters.get(param_id)

    def parameter_count(self) -> int:
        return len(self.parameters)

    def parameters_list(self) -> list[Parameter]:
        """Параметры, отсортированные по label."""
        return sorted(
            self.parameters.values(),
            key=lambda p: (p.label or p.name).lower(),
        )

    # ------------------------------------------------------------
    # REFERENCE IMAGE
    # ------------------------------------------------------------

    def set_reference_image(self, ref: ReferenceImage | None) -> None:
        self.reference_image = ref

    def has_reference_image(self) -> bool:
        return (
            self.reference_image is not None
            and self.reference_image.is_valid()
        )

    def clear_reference_image(self) -> None:
        self.reference_image = None

    def prune_parameters(self) -> None:
        """Удалить таргеты, ссылающиеся на несуществующие группы.

        Параметр без таргетов остаётся — пользователь может
        потом перепривязать его или удалить вручную.
        """
        valid_ids = set(self.semantic_groups.keys())
        for param in self.parameters.values():
            param.targets = [
                t for t in param.targets if t.group_id in valid_ids
            ]
