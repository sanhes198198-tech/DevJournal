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
from .component import Component
from .visibility_rule import VisibilityRule
from .vector_layer import VectorLayer
from .mounting import MountPoint, apply_migration


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
        components: dict | None = None,
        semantic_groups: dict | None = None,
        parameters: dict | None = None,
        generation_rules: dict | None = None,
    ):
        self.id = asset_id or self._generate_id()
        self.name = name
        self.type = type_ if type_ in ASSET_TYPE_IDS else "other"
        self.geometry = geometry or self._empty_geometry()
        # Ссылки на другие Asset'ы (составной Asset).
        # Либо geometry с контуром, либо components — но не оба.
        self.components: dict[str, Component] = components or {}
        self.visibility_rules: dict[str, VisibilityRule] = {}
        self.semantic_groups: dict[str, SemanticGroup] = semantic_groups or {}
        self.parameters = parameters or {}
        self.reference_image: ReferenceImage | None = None
        self.generation_rules = generation_rules or self._default_rules()
        # V13: опорная линия (ground line) для композита.
        # ground_line_y = None — линии нет.
        # ground_line_visible — показывать ли пунктир.
        self.ground_line_y: float | None = None
        self.ground_line_visible: bool = True
        # V16: слои. Пока только модель — UI позже.
        # При загрузке старого JSON создаётся один слой из geometry.
        self.layers: list[VectorLayer] = []

        # V22 (Mounting): точки крепления (новая модель).
        # Пусто для новых ассетов; заполняется через apply_migration
        # при загрузке старого JSON без поля "mountpoints".
        self.mountpoints: list[MountPoint] = []

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
            "arcs": [],
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
            "arcs": [
                [a, b, float(v)]
                for (a, b), v in getattr(contour, "arcs", {}).items()
                if a in valid_all_ids and b in valid_all_ids
                and abs(v) > 1e-9
            ],
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
            "components": {
                cid: c.to_dict()
                for cid, c in self.components.items()
            },
            "visibility_rules": {
                rid: r.to_dict()
                for rid, r in self.visibility_rules.items()
            },
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
            "ground_line_y": self.ground_line_y,
            "ground_line_visible": self.ground_line_visible,
            "layers": [l.to_dict() for l in self.layers],
            "mountpoints": [
                mp.to_dict() for mp in self.mountpoints
            ],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Asset":
        # V22: было ли поле mountpoints в исходном JSON.
        # Если нет — это старый ассет, мигрируем legacy в конце.
        _has_mountpoints_field = "mountpoints" in d

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

        rules_raw = d.get("visibility_rules") or {}
        rules: dict[str, VisibilityRule] = {}
        if isinstance(rules_raw, dict):
            for rid, rdict in rules_raw.items():
                if not isinstance(rdict, dict):
                    continue
                try:
                    rules[rid] = VisibilityRule.from_dict(rdict)
                except Exception:
                    continue

        comp_raw = d.get("components") or {}
        comps: dict[str, Component] = {}
        if isinstance(comp_raw, dict):
            for cid, cdict in comp_raw.items():
                if not isinstance(cdict, dict):
                    continue
                try:
                    comps[cid] = Component.from_dict(cdict)
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
            components=comps,
            semantic_groups=groups,
            parameters=params,
            generation_rules=d.get("generation_rules") or cls._default_rules(),
        )
        asset.reference_image = ref
        asset.visibility_rules = rules

        # V13: ground line
        g_y = d.get("ground_line_y")
        if isinstance(g_y, (int, float)):
            asset.ground_line_y = float(g_y)
        else:
            asset.ground_line_y = None
        asset.ground_line_visible = bool(
            d.get("ground_line_visible", True)
        )

        # V16: слои
        layers_raw = d.get("layers") or []
        if layers_raw:
            for ldict in layers_raw:
                if not isinstance(ldict, dict):
                    continue
                try:
                    asset.layers.append(VectorLayer.from_dict(ldict))
                except Exception:
                    continue
        else:
            # Автомиграция: старый JSON без layers —
            # создать один слой из geometry.
            asset.layers.append(VectorLayer(
                name="Основной",
                geometry=dict(asset.geometry),
            ))

        # V22 (Mounting): читаем mountpoints из JSON
        mps_raw = d.get("mountpoints")
        if isinstance(mps_raw, list):
            for mdict in mps_raw:
                if not isinstance(mdict, dict):
                    continue
                try:
                    asset.mountpoints.append(
                        MountPoint.from_dict(mdict)
                    )
                except Exception:
                    continue

        # V22: если поля mountpoints не было — мигрируем legacy
        # (semantic_groups + auto_rule -> MountPoint).
        # Миграция идемпотентна и не мутирует semantic_groups.
        if not _has_mountpoints_field:
            try:
                apply_migration(asset)
            except Exception:
                pass

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
    # ANCHORS (V8c)
    # ------------------------------------------------------------

    def anchors(self) -> dict[str, tuple[float, float]]:
        """Точки крепления из групп с префиксом `anchor_`.

        Position = центроид узлов группы. Если узлы не найдены
        (или группа пуста) — anchor пропускается.

        Возвращает {tag: (x, y)}. tag — имя без префикса.
        """
        result: dict[str, tuple[float, float]] = {}

        # V16: точки из ВСЕХ видимых слоёв (не только активного).
        # Раньше anchors терялись, если anchor_bottom был
        # в неактивном слое окна.
        pts_by_id: dict[str, tuple[float, float]] = {}

        layers = getattr(self, "layers", None) or []
        layer_geometries = []
        if layers:
            for layer in layers:
                if not getattr(layer, "visible", True):
                    continue
                layer_geometries.append(layer.geometry or {})
        if not layer_geometries:
            # Старый формат — один слой в geometry
            layer_geometries = [self.geometry]

        for g in layer_geometries:
            contour = g.get("contour", [])
            node_ids = g.get("node_ids", [])
            for i, nid in enumerate(node_ids):
                if i < len(contour):
                    x, y = contour[i]
                    pts_by_id[nid] = (float(x), float(y))
            extra_pts = g.get("extra_points", [])
            extra_ids = g.get("extra_node_ids", [])
            for i, nid in enumerate(extra_ids):
                if i < len(extra_pts):
                    x, y = extra_pts[i]
                    pts_by_id[nid] = (float(x), float(y))

        # Маппинг имён групп в теги anchor'ов.
        # Один и тот же смысл у стены и у крыши может называться
        # по-разному — приводим к единому tag.
        _ALIASES = {
            "anchor_top": "top",
            "top": "top",
            "anchor_bottom": "bottom",
            "bottom": "bottom",
            "foundation": "bottom",
            "anchor_foundation": "bottom",
            "anchor_face": "face",
            "facade": "face",
            "anchor_facade": "face",
            "anchor_left": "left",
            "side_left": "left",
            "anchor_right": "right",
            "side_right": "right",
        }

        # ПРОХОД 1: anchor_* группы имеют ПРИОРИТЕТ.
        # Фиксит ситуацию, когда группа "top"/"foundation"
        # перекрывает явную anchor-группу.
        for group in self.semantic_groups.values():
            gname = getattr(group, "name", "")
            if not gname.startswith("anchor_"):
                continue
            tag = _ALIASES.get(gname)
            if tag is None:
                continue

            xs, ys = [], []
            for nid in group.node_ids:
                p = pts_by_id.get(nid)
                if p is not None:
                    xs.append(p[0])
                    ys.append(p[1])

            if not xs:
                continue

            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)
            if tag not in result:
                result[tag] = (cx, cy)

        # ПРОХОД 2: обычные группы (top/foundation/left/right/...).
        # Заполняют только те теги, которые ещё не закрыты.
        for group in self.semantic_groups.values():
            gname = getattr(group, "name", "")
            if gname.startswith("anchor_"):
                continue
            tag = _ALIASES.get(gname)
            if tag is None:
                continue

            xs, ys = [], []
            for nid in group.node_ids:
                p = pts_by_id.get(nid)
                if p is not None:
                    xs.append(p[0])
                    ys.append(p[1])

            if not xs:
                continue

            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)
            if tag not in result:
                result[tag] = (cx, cy)

        return result

    # ------------------------------------------------------------
    # COMPONENTS (V8a)
    # ------------------------------------------------------------

    def is_composite(self) -> bool:
        """True, если Asset состоит из ссылок на другие Asset'ы."""
        return len(self.components) > 0

    def component_count(self) -> int:
        return len(self.components)

    def add_component(self, comp: Component) -> bool:
        """Добавить компонент. False, если self-ref или дубликат."""
        if not comp.is_valid():
            return False

        # Запрет self-reference
        if comp.asset_id == self.id:
            return False

        if comp.id in self.components:
            return False

        self.components[comp.id] = comp
        return True

    def remove_component(self, comp_id: str) -> Component | None:
        return self.components.pop(comp_id, None)

    def get_component(self, comp_id: str) -> Component | None:
        return self.components.get(comp_id)

    def components_list(self) -> list[Component]:
        return sorted(
            self.components.values(),
            key=lambda c: (c.name or c.id).lower(),
        )

    def validate_components(self) -> list[str]:
        """Проверка: self-ref, дубликаты, пустые ссылки."""
        problems: list[str] = []
        seen_ids = set()

        for cid, comp in self.components.items():
            if not comp.asset_id:
                problems.append(f"{cid}: пустой asset_id")
            if comp.asset_id == self.id:
                problems.append(f"{cid}: self-reference")
            if comp.id in seen_ids:
                problems.append(f"{cid}: дубликат id")
            seen_ids.add(comp.id)

        return problems

    # ------------------------------------------------------------
    # VISIBILITY RULES (V9b)
    # ------------------------------------------------------------

    def add_visibility_rule(self, rule: VisibilityRule) -> bool:
        if not rule.is_valid():
            return False
        if rule.id in self.visibility_rules:
            return False
        self.visibility_rules[rule.id] = rule
        return True

    def remove_visibility_rule(
        self, rule_id: str,
    ) -> VisibilityRule | None:
        return self.visibility_rules.pop(rule_id, None)

    def get_visibility_rule(
        self, rule_id: str,
    ) -> VisibilityRule | None:
        return self.visibility_rules.get(rule_id)

    def visibility_rules_list(self) -> list[VisibilityRule]:
        return sorted(
            self.visibility_rules.values(),
            key=lambda r: (r.label or r.name).lower(),
        )

    def visibility_rule_count(self) -> int:
        return len(self.visibility_rules)

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
