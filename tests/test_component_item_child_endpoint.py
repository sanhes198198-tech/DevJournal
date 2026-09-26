import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.constructor.view.items.component_item import ComponentItem
from app.vector_editor.model import Asset, Component, Parameter, ParameterTarget, SemanticGroup


def _make_item(points, groups, *, overrides=None, parameters=None, mountpoints=None):
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
            id=group_id, name=name, node_ids=group_node_ids,
        )
        for group_id, name, group_node_ids in groups
    }
    asset = Asset(
        geometry=geometry,
        semantic_groups=semantic_groups,
        parameters=parameters or {},
    )
    asset.mountpoints = list(mountpoints or [])
    return ComponentItem(
        Component(param_overrides=overrides), asset=asset,
    ), asset


class ComponentItemChildEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_resolves_bottom_alias(self):
        item, _ = _make_item(
            {"n0": (0.0, 0.0), "n1": (2.0, 0.0), "n2": (10.0, 4.0)},
            [("g_bottom", "anchor_bottom", ["n0", "n1"])],
        )

        result = item.resolve_child_endpoint("bottom")

        self.assertEqual(result["local_position"], (-4.0, -2.0))
        self.assertEqual(result["source"], "legacy_anchor")
        self.assertEqual(result["alias"], "bottom")
        self.assertTrue(result["resolved"])
        self.assertIsNone(result["diagnostic"])

    def test_resolves_top_alias(self):
        item, _ = _make_item(
            {"n0": (0.0, 0.0), "n1": (2.0, 0.0), "n2": (10.0, 4.0)},
            [("g_top", "anchor_top", ["n1", "n2"])],
        )

        result = item.resolve_child_endpoint("top")

        self.assertEqual(
            result["local_position"], item.anchors_local()["top"]
        )
        self.assertTrue(result["resolved"])

    def test_uses_anchor_group_priority_from_anchors_local(self):
        item, _ = _make_item(
            {
                "n0": (0.0, 0.0), "n1": (2.0, 0.0),
                "n2": (10.0, 10.0), "n3": (14.0, 10.0),
            },
            [
                ("g_top", "top", ["n0", "n1"]),
                ("g_anchor_top", "anchor_top", ["n2", "n3"]),
            ],
        )

        result = item.resolve_child_endpoint("top")

        self.assertEqual(
            result["local_position"], item.anchors_local()["top"]
        )
        self.assertEqual(result["local_position"], (5.0, 5.0))

    def test_uses_existing_param_override_anchor_calculation(self):
        item, _ = _make_item(
            {"n0": (0.0, 0.0), "n1": (2.0, 0.0), "n2": (10.0, 4.0)},
            [
                ("g_bottom", "anchor_bottom", ["n0", "n1"]),
                ("g_shift", "shift", ["n0", "n1"]),
            ],
            overrides={"width": 2.0},
            parameters={
                "width": Parameter(
                    name="width", value=0.0,
                    targets=[ParameterTarget("g_shift", koef_x=1.0)],
                )
            },
        )

        result = item.resolve_child_endpoint("bottom")

        self.assertEqual(
            result["local_position"], item.anchors_local()["bottom"]
        )
        self.assertEqual(result["local_position"], (-2.0, -2.0))

    def test_tracks_changed_group_geometry(self):
        item, asset = _make_item(
            {"n0": (0.0, 0.0), "n1": (2.0, 0.0), "n2": (10.0, 4.0)},
            [("g_bottom", "anchor_bottom", ["n0", "n1"])],
        )
        before = item.resolve_child_endpoint("bottom")["local_position"]

        asset.geometry["contour"][0] = (2.0, 0.0)
        asset.geometry["contour"][1] = (4.0, 0.0)
        item._rebuild_paths()
        after = item.resolve_child_endpoint("bottom")["local_position"]

        self.assertNotEqual(before, after)
        self.assertEqual(after, (-3.0, -2.0))

    def test_unknown_alias_returns_unresolved_descriptor(self):
        item, _ = _make_item(
            {"n0": (0.0, 0.0)},
            [("g_bottom", "anchor_bottom", ["n0"])],
        )

        result = item.resolve_child_endpoint("missing")

        self.assertEqual(result["local_position"], None)
        self.assertEqual(result["source"], "legacy_anchor")
        self.assertEqual(result["alias"], "missing")
        self.assertFalse(result["resolved"])
        self.assertIsInstance(result["diagnostic"], str)

    def test_missing_mountpoint_does_not_block_legacy_alias(self):
        item, asset = _make_item(
            {"n0": (0.0, 0.0), "n1": (2.0, 0.0), "n2": (10.0, 4.0)},
            [("g_bottom", "anchor_bottom", ["n0", "n1"])],
        )

        self.assertEqual(asset.mountpoints, [])
        result = item.resolve_child_endpoint("bottom")

        self.assertTrue(result["resolved"])
        self.assertEqual(
            result["local_position"], item.anchors_local()["bottom"]
        )

    def test_returns_item_local_coordinate_and_empty_alias_is_absent(self):
        item, _ = _make_item(
            {"n0": (0.0, 0.0), "n1": (2.0, 0.0), "n2": (10.0, 4.0)},
            [("g_bottom", "anchor_bottom", ["n0", "n1"])],
        )

        result = item.resolve_child_endpoint("bottom")

        self.assertEqual(
            result["local_position"], item.anchors_local()["bottom"]
        )
        self.assertEqual(result["local_position"], (-4.0, -2.0))
        self.assertIsNone(item.resolve_child_endpoint(""))


if __name__ == "__main__":
    unittest.main()
