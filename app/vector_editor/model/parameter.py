"""
Parameter / ParameterTarget — параметрическая связь Asset'а.

Модель чистая, без Qt. Работает со словарями SemanticGroup,
не ссылается на Asset.

Идея:
  Parameter(value) —> targets = [(group, koef_x, koef_y), ...]
  Изменение value на delta —> каждый узел таргетной группы
  сдвигается на (delta*koef_x, delta*koef_y).

Если узел входит в несколько групп-таргетов, вклады
суммируются по узлу и применяются ОДИН раз.
"""

from __future__ import annotations

import uuid


class ParameterTarget:
    """Один таргет параметра — группа + коэффициенты сдвига."""

    def __init__(
        self,
        group_id: str,
        koef_x: float = 1.0,
        koef_y: float = 0.0,
    ):
        self.group_id = group_id
        self.koef_x = float(koef_x)
        self.koef_y = float(koef_y)

    # ------------------------------------------------------------

    def is_zero(self) -> bool:
        return (
            abs(self.koef_x) < 1e-12 and abs(self.koef_y) < 1e-12
        )

    def to_dict(self) -> dict:
        return {
            "group_id": self.group_id,
            "koef_x": self.koef_x,
            "koef_y": self.koef_y,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ParameterTarget":
        return cls(
            group_id=str(d.get("group_id", "")),
            koef_x=float(d.get("koef_x", 1.0)),
            koef_y=float(d.get("koef_y", 0.0)),
        )


class Parameter:
    """Именованный параметр Asset'а."""

    def __init__(
        self,
        id: str | None = None,
        name: str = "param",
        label: str = "Параметр",
        value: float = 0.0,
        unit: str = "м",
        targets: list[ParameterTarget] | None = None,
    ):
        self.id = id or self._generate_id()
        self.name = name
        self.label = label
        self.value = float(value)
        self.unit = unit
        self.targets: list[ParameterTarget] = list(targets or [])

    @staticmethod
    def _generate_id() -> str:
        return "p_" + uuid.uuid4().hex[:8]

    # ------------------------------------------------------------

    def add_target(self, target: ParameterTarget) -> None:
        self.targets.append(target)

    def remove_target(self, group_id: str) -> bool:
        before = len(self.targets)
        self.targets = [
            t for t in self.targets if t.group_id != group_id
        ]
        return len(self.targets) < before

    def target_count(self) -> int:
        return len(self.targets)

    def target_group_ids(self) -> list[str]:
        return [t.group_id for t in self.targets]

    # ------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "label": self.label,
            "value": self.value,
            "unit": self.unit,
            "targets": [t.to_dict() for t in self.targets],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Parameter":
        raw_targets = d.get("targets") or []
        targets = []
        for td in raw_targets:
            if not isinstance(td, dict):
                continue
            try:
                targets.append(ParameterTarget.from_dict(td))
            except Exception:
                continue

        return cls(
            id=d.get("id"),
            name=d.get("name", "param"),
            label=d.get("label", "Параметр"),
            value=float(d.get("value", 0.0)),
            unit=d.get("unit", "м"),
            targets=targets,
        )


# ================================================================
# COMPUTE
# ================================================================

def compute_delta_for_parameter(
    parameter: Parameter,
    delta: float,
    semantic_groups: dict,
) -> dict[str, tuple[float, float]]:
    """Сдвиг узлов от изменения ОДНОГО параметра.

    Возвращает {node_id: (dx, dy)}.
    Узлы, входящие в несколько таргетов одного параметра, получают
    сумму вкладов (правило суммирования).
    """
    result: dict[str, tuple[float, float]] = {}

    if abs(delta) < 1e-12:
        return result

    for target in parameter.targets:
        if target.is_zero():
            continue

        group = semantic_groups.get(target.group_id)
        if group is None:
            continue

        dx = delta * target.koef_x
        dy = delta * target.koef_y

        for nid in group.node_ids:
            prev = result.get(nid, (0.0, 0.0))
            result[nid] = (prev[0] + dx, prev[1] + dy)

    return result


def compute_combined_delta(
    changes: list[tuple[Parameter, float]],
    semantic_groups: dict,
) -> dict[str, tuple[float, float]]:
    """Суммарный сдвиг от нескольких изменений сразу.

    changes = [(parameter, delta), ...]

    Если узел входит в несколько групп-таргетов разных параметров —
    вклады складываются. Каждый узел упоминается в результате
    РОВНО один раз.
    """
    total: dict[str, tuple[float, float]] = {}

    for param, delta in changes:
        part = compute_delta_for_parameter(
            param, delta, semantic_groups,
        )
        for nid, (dx, dy) in part.items():
            prev = total.get(nid, (0.0, 0.0))
            total[nid] = (prev[0] + dx, prev[1] + dy)

    return total


def apply_delta_to_points(
    points: list[tuple[float, float]],
    node_ids: list[str],
    delta: dict[str, tuple[float, float]],
) -> list[tuple[float, float]]:
    """Применить delta {node_id: (dx, dy)} к точкам.

    Возвращает НОВЫЙ список точек (не мутирует исходный).
    """
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    result = list(points)

    for nid, (dx, dy) in delta.items():
        idx = id_to_idx.get(nid)
        if idx is None:
            continue
        x, y = result[idx]
        result[idx] = (x + dx, y + dy)

    return result
