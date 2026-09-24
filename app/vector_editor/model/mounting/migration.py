"""
Миграция legacy semantic_groups + auto_rule -> MountPoint[].

Старые ассеты хранят точки крепления в semantic_groups с auto_rule.
Новая модель - MountPoint с role, position, distribution.

Правила миграции:
  - role = None (не угадываем)
  - position = центроид узлов-шаблонов группы
  - distribution = default (count=1)
  - legacy_group_id / legacy_auto_rule сохраняются как есть

Функция НЕ мутирует Asset. Возвращает список MountPoint.
Интеграция в Asset - отдельный этап.
"""

from __future__ import annotations

from .mount_point import MountPoint, Distribution


def _collect_points_by_id(asset) -> dict[str, tuple[float, float]]:
    """Собрать все node_id -> (x, y) из видимых слоёв Asset.

    Тот же обход что в Asset.anchors() - только visible слои,
    fallback на asset.geometry если слоёв нет.
    """
    pts: dict[str, tuple[float, float]] = {}

    layers = getattr(asset, "layers", None) or []
    geometries = []
    if layers:
        for layer in layers:
            if not getattr(layer, "visible", True):
                continue
            geometries.append(layer.geometry or {})
    if not geometries:
        geometries = [getattr(asset, "geometry", {}) or {}]

    for g in geometries:
        contour = g.get("contour", []) or []
        node_ids = g.get("node_ids", []) or []
        for i, nid in enumerate(node_ids):
            if i < len(contour):
                x, y = contour[i]
                pts[nid] = (float(x), float(y))

        extra_pts = g.get("extra_points", []) or []
        extra_ids = g.get("extra_node_ids", []) or []
        for i, nid in enumerate(extra_ids):
            if i < len(extra_pts):
                x, y = extra_pts[i]
                pts[nid] = (float(x), float(y))

    return pts


def _group_centroid(
    group, pts_by_id: dict[str, tuple[float, float]],
) -> tuple[float, float] | None:
    """Центроид узлов группы. None если ни одного узла нет."""
    xs, ys = [], []
    for nid in group.node_ids:
        p = pts_by_id.get(nid)
        if p is not None:
            xs.append(p[0])
            ys.append(p[1])
    if not xs:
        return None
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def migrate_asset(asset) -> list[MountPoint]:
    """Извлечь MountPoint[] из legacy semantic_groups с auto_rule.

    Группы без auto_rule игнорируются (это anchors / параметризация).
    Возвращает новый список, Asset не мутируется.
    """
    result: list[MountPoint] = []

    groups = getattr(asset, "semantic_groups", None) or {}
    if not groups:
        return result

    pts_by_id = _collect_points_by_id(asset)
    if not pts_by_id:
        return result

    for gid, group in groups.items():
        auto_rule = getattr(group, "auto_rule", None)
        if not auto_rule:
            continue

        centroid = _group_centroid(group, pts_by_id)
        if centroid is None:
            continue

        mp = MountPoint(
            role=None,
            position=centroid,
            distribution=Distribution(),
            legacy_group_id=gid,
            legacy_auto_rule=auto_rule,
        )
        result.append(mp)

    return result


def apply_migration(asset) -> int:
    """Заполнить asset.mountpoints результатом migrate_asset.

    Возвращает количество добавленных MountPoint.
    Если у asset уже есть непустой mountpoints - не трогает.
    """
    existing = getattr(asset, "mountpoints", None)
    if existing:
        return 0

    migrated = migrate_asset(asset)
    if not migrated:
        return 0

    asset.mountpoints = migrated
    return len(migrated)
