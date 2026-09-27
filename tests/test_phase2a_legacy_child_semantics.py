import json
import os
import unittest
from collections import Counter
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.constructor.view.items.component_item import ComponentItem
from app.vector_editor.model import (
    Asset,
    Component,
    Parameter,
    ParameterTarget,
    SemanticGroup,
)
from app.vector_editor.model.mounting.attachment import (
    Attachment,
    endpoint_from_component_value,
)


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "app" / "vector_editor" / "assets"


def _rows(value):
    if isinstance(value, dict):
        return list(value.values())
    if isinstance(value, list):
        return value
    return []


def _load_asset_data(asset_id):
    path = ASSET_DIR / f"{asset_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _load_asset(asset_id):
    return Asset.from_dict(_load_asset_data(asset_id))


def _find_component_record(asset_id, component_id):
    data = _load_asset_data(asset_id)
    component = next(
        row for row in _rows(data.get("components"))
        if row.get("id") == component_id
    )
    return data, component


def _node_points(asset):
    points = {}
    layers = getattr(asset, "layers", None) or []
    geometries = [
        layer.geometry or {}
        for layer in layers
        if getattr(layer, "visible", True)
    ]
    if not geometries:
        geometries = [getattr(asset, "geometry", {}) or {}]

    for geometry in geometries:
        contour = geometry.get("contour", []) or []
        node_ids = geometry.get("node_ids", []) or []
        for index, node_id in enumerate(node_ids):
            if index < len(contour):
                points[node_id] = tuple(map(float, contour[index]))

        extra_points = geometry.get("extra_points", []) or []
        extra_ids = geometry.get("extra_node_ids", []) or []
        for index, node_id in enumerate(extra_ids):
            if index < len(extra_points):
                points[node_id] = tuple(map(float, extra_points[index]))
    return points


def _group_centroid(asset, group):
    points = _node_points(asset)
    found = [points[node_id] for node_id in group.node_ids if node_id in points]
    if not found:
        return None
    return (
        sum(point[0] for point in found) / len(found),
        sum(point[1] for point in found) / len(found),
    )


def _synthetic_asset(points, groups, *, parameters=None):
    node_ids = list(points)
    geometry = {
        "contour": [points[node_id] for node_id in node_ids],
        "closed": False,
        "units": "m",
        "node_ids": node_ids,
        "groups": {},
        "extra_edges": [],
        "arcs": [],
        "extra_points": [],
        "extra_node_ids": [],
    }
    semantic_groups = {
        group_id: SemanticGroup(
            id=group_id,
            name=name,
            node_ids=group_node_ids,
        )
        for group_id, name, group_node_ids in groups
    }
    return Asset(
        geometry=geometry,
        semantic_groups=semantic_groups,
        parameters=parameters or {},
    )


class Phase2ALegacyChildSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_real_anchor_groups_keep_anchor_prefix_priority(self):
        bottom_asset = _load_asset("2d7f96953f11")
        self.assertEqual(
            bottom_asset.semantic_groups["g_9e8230a6"].name,
            "anchor_bottom",
        )
        self.assertEqual(
            bottom_asset.semantic_groups["g_012a26ce"].name,
            "bottom",
        )
        bottom_anchor = bottom_asset.anchors()["bottom"]
        bottom_explicit = _group_centroid(
            bottom_asset, bottom_asset.semantic_groups["g_9e8230a6"],
        )
        bottom_fallback = _group_centroid(
            bottom_asset, bottom_asset.semantic_groups["g_012a26ce"],
        )
        self.assertEqual(bottom_anchor, bottom_explicit)
        self.assertNotEqual(bottom_anchor, bottom_fallback)

        top_asset = _load_asset("3ec907f2b564")
        self.assertEqual(
            top_asset.semantic_groups["g_a2273079"].name,
            "anchor_top",
        )
        self.assertEqual(
            top_asset.semantic_groups["g_0c679b98"].name,
            "top",
        )
        top_anchor = top_asset.anchors()["top"]
        top_explicit = _group_centroid(
            top_asset, top_asset.semantic_groups["g_a2273079"],
        )
        top_fallback = _group_centroid(
            top_asset, top_asset.semantic_groups["g_0c679b98"],
        )
        self.assertEqual(top_anchor, top_explicit)
        self.assertNotEqual(top_anchor, top_fallback)

    def test_asset_anchor_tracks_changes_to_group_node_geometry(self):
        asset = _synthetic_asset(
            {"n0": (0.0, 0.0), "n1": (2.0, 0.0), "n2": (10.0, 4.0)},
            [("g_bottom", "anchor_bottom", ["n0", "n1"])],
        )
        before = asset.anchors()["bottom"]

        asset.geometry["contour"][0] = (2.0, 2.0)
        asset.geometry["contour"][1] = (4.0, 2.0)
        after = asset.anchors()["bottom"]

        self.assertEqual(before, (1.0, 0.0))
        self.assertEqual(after, (3.0, 2.0))

    def test_component_item_anchor_tracks_changed_group_geometry(self):
        asset = _synthetic_asset(
            {"n0": (0.0, 0.0), "n1": (2.0, 0.0), "n2": (10.0, 4.0)},
            [("g_bottom", "anchor_bottom", ["n0", "n1"])],
        )
        item = ComponentItem(Component(attach_anchor="bottom"), asset=asset)
        before = item.anchors_local()["bottom"]

        asset.geometry["contour"][0] = (2.0, 2.0)
        asset.geometry["contour"][1] = (4.0, 2.0)
        item._rebuild_paths()
        after = item.anchors_local()["bottom"]

        self.assertNotEqual(before, after)

    def test_existing_real_param_overrides_preserve_native_child_endpoint(self):
        checked = 0
        for composite_path in ASSET_DIR.glob("*.json"):
            if composite_path.name == "_folders.json":
                continue
            composite = json.loads(composite_path.read_text(encoding="utf-8"))
            for record in _rows(composite.get("components")):
                address = record.get("attach_location")
                overrides = record.get("param_overrides") or {}
                if not address or not overrides:
                    continue
                self.assertIsNone(record.get("attach_anchor"))

                child_data = _load_asset_data(record["asset_id"])
                actual_item = ComponentItem(
                    Component.from_dict(record),
                    asset=Asset.from_dict(child_data),
                )
                baseline_component = Component.from_dict(record)
                baseline_component.param_overrides = {}
                baseline_item = ComponentItem(
                    baseline_component,
                    asset=Asset.from_dict(child_data),
                )

                actual_endpoint = actual_item.resolve_child_endpoint(None)
                baseline_endpoint = baseline_item.resolve_child_endpoint(None)
                self.assertTrue(actual_endpoint["resolved"])
                self.assertTrue(baseline_endpoint["resolved"])
                self.assertEqual(
                    actual_endpoint["local_position"],
                    baseline_endpoint["local_position"],
                    "current override unexpectedly moves native endpoint: "
                    f"{composite_path.name}/{record.get('id')}",
                )
                checked += 1

        self.assertEqual(checked, 12)

    def test_override_that_targets_anchor_group_moves_item_local_endpoint(self):
        asset = _synthetic_asset(
            {"n0": (0.0, 0.0), "n1": (2.0, 0.0), "n2": (10.0, 4.0)},
            [("g_anchor", "anchor_bottom", ["n0", "n1"])],
            parameters={
                "height": Parameter(
                    name="height",
                    value=0.0,
                    targets=[
                        ParameterTarget(
                            "g_anchor", koef_x=0.0, koef_y=1.0,
                        ),
                    ],
                ),
            },
        )
        item = ComponentItem(Component(attach_anchor="bottom"), asset=asset)
        before = item.anchors_local()["bottom"]

        item._component.param_overrides["height"] = 2.0
        after = item.anchors_local()["bottom"]

        self.assertAlmostEqual(after[0], before[0])
        self.assertAlmostEqual(after[1] - before[1], 2.0)

    def test_all_migrated_links_persist_native_without_legacy_aliases(self):
        checked = 0
        for composite_path in ASSET_DIR.glob("*.json"):
            if composite_path.name == "_folders.json":
                continue
            composite = json.loads(composite_path.read_text(encoding="utf-8"))
            for record in _rows(composite.get("components")):
                if not record.get("attach_location"):
                    continue

                self.assertIsNone(record.get("attach_anchor"))
                component = Component.from_dict(record)
                self.assertIsNone(component.attach_anchor)
                self.assertTrue(component.attach_location)
                checked += 1

        self.assertEqual(checked, 27)

    def test_ambiguous_real_asset_remains_legacy_and_keeps_first_group_priority(self):
        asset = _load_asset("9c545d9ccbfa")
        candidates = [
            group for group in asset.semantic_groups.values()
            if group.name == "anchor_bottom"
        ]
        self.assertEqual(len(candidates), 5)
        self.assertEqual(candidates[0].id, "g_013e323d")

        candidate_centroids = [
            _group_centroid(asset, group) for group in candidates
        ]
        self.assertEqual(len(set(candidate_centroids)), 4)

        descriptor = endpoint_from_component_value(
            "bottom", field="attach_anchor",
        )
        self.assertEqual(descriptor["kind"], "legacy_anchor")
        mountpoints_before = [mp.to_dict() for mp in asset.mountpoints]
        position, source = Attachment(
            target_type="anchor", target_id="bottom",
        ).resolve(asset)

        self.assertEqual(source, "legacy_anchor")
        self.assertEqual(position, candidate_centroids[0])
        self.assertEqual(
            [mp.to_dict() for mp in asset.mountpoints], mountpoints_before,
        )

    def test_existing_mountpoint_does_not_replace_legacy_bottom_alias(self):
        asset = _load_asset("25f092d12df4")
        self.assertEqual(len(asset.mountpoints), 1)
        self.assertEqual(asset.mountpoints[0].id, "mp_f9babe5c")

        position, source = Attachment(
            target_type="anchor", target_id="bottom",
        ).resolve(asset)
        self.assertEqual(source, "legacy_anchor")
        self.assertEqual(position, asset.anchors()["bottom"])
        self.assertNotEqual(position, asset.mountpoints[0].position)

        item = ComponentItem(
            Component(attach_anchor="bottom"), asset=asset,
        )
        endpoint = item.resolve_child_endpoint("bottom")
        self.assertTrue(endpoint["resolved"])
        self.assertEqual(
            endpoint["local_position"], item.anchors_local()["bottom"],
        )


if __name__ == "__main__":
    unittest.main()
