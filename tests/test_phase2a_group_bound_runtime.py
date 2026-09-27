import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication, QGraphicsScene

from app.constructor.reflow_engine import reflow_from
from app.constructor.snap_resolver import find_mount_snap
from app.constructor.view.items.component_item import ComponentItem
from app.vector_editor.model import Asset, Component, Parameter, ParameterTarget, SemanticGroup
from app.vector_editor.model.mounting import MountPoint


def _make_asset(*, asset_type="other", overrides=None, group_bound=True):
    points = {
        "n0": (0.0, 0.0),
        "n1": (4.0, 0.0),
        "n2": (8.0, 4.0),
        "n3": (0.0, 4.0),
    }
    geometry = {
        "contour": [list(point) for point in points.values()],
        "closed": True,
        "units": "m",
        "node_ids": list(points),
        "groups": {},
        "extra_edges": [],
        "arcs": [],
        "extra_points": [],
        "extra_node_ids": [],
    }
    asset = Asset(
        type_=asset_type,
        geometry=geometry,
        semantic_groups={
            "g_endpoint": SemanticGroup(
                id="g_endpoint",
                name="anchor_bottom",
                node_ids=["n0", "n1"],
            ),
            "g_shift": SemanticGroup(
                id="g_shift",
                name="height_shift",
                node_ids=["n0", "n1"],
            ),
        },
        parameters={
            "p_height": Parameter(
                id="p_height",
                name="height",
                value=0.0,
                targets=[
                    ParameterTarget(
                        "g_shift", koef_x=0.0, koef_y=1.0,
                    ),
                ],
            ),
        },
    )
    if group_bound:
        asset.mountpoints = [
            MountPoint(
                id="mp_endpoint",
                role="window",
                position=(100.0, 100.0),
                semantic_group_id="g_endpoint",
            ),
        ]
    component = Component(
        id="component",
        asset_id=asset.id,
        param_overrides=overrides,
    )
    return ComponentItem(component, asset=asset), asset


class _Composite:
    def __init__(self, components):
        self.components = components

    def get_component(self, component_id):
        return self.components.get(component_id)


class GroupBoundMountPointRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_mount_locations_use_live_group_and_component_parameter_overrides(self):
        item, _asset = _make_asset(overrides={"height": 2.0})

        location = item.mount_locations_local()["mp_endpoint"][0]
        legacy_anchor = item.anchors_local()["bottom"]

        self.assertEqual(location[:3], (0, 0, "window"))
        self.assertAlmostEqual(location[3], legacy_anchor[0])
        self.assertAlmostEqual(location[4], legacy_anchor[1])

        item.component.set_param_override("height", 4.0)
        item.prepareGeometryChange()
        item._rebuild_paths()
        updated_location = item.mount_locations_local()["mp_endpoint"][0]
        updated_legacy_anchor = item.anchors_local()["bottom"]

        self.assertNotEqual(location[4], updated_location[4])
        self.assertAlmostEqual(updated_location[3], updated_legacy_anchor[0])
        self.assertAlmostEqual(updated_location[4], updated_legacy_anchor[1])

    def test_snap_resolver_sees_group_bound_mountpoint_in_scene_coordinates(self):
        parent_item, _asset = _make_asset(overrides={"height": 2.0})
        parent_item.component.id = "parent"
        parent_item.setPos(10.0, 20.0)

        moving_item, moving_asset = _make_asset(
            asset_type="window", group_bound=False,
        )
        moving_item.component.id = "moving"
        moving_item.component.role = None

        scene = QGraphicsScene()
        scene.addItem(parent_item)
        scene.addItem(moving_item)

        locations = parent_item.mount_locations_world()["mp_endpoint"]
        _ix, _iy, role, sx, sy = locations[0]
        self.assertEqual(role, "window")

        result = find_mount_snap(
            scene,
            moving_item,
            (sx, sy),
            "window",
            0.01,
            ComponentItem,
        )

        self.assertIsNotNone(result)
        self.assertIs(result.other_item, parent_item)
        self.assertEqual(result.their_tag, "mp_endpoint__0__0")
        self.assertEqual(
            result.their_location,
            {
                "mountpoint_id": "mp_endpoint",
                "index_x": 0,
                "index_y": 0,
            },
        )
        self.assertAlmostEqual(result.dx, 0.0)
        self.assertAlmostEqual(result.dy, 0.0)

    def test_reflow_uses_group_bound_parent_location_and_legacy_child_endpoint(self):
        parent_item, _parent_asset = _make_asset(
            overrides={"height": 2.0},
        )
        parent_item.component.id = "parent"
        parent_item.component.x = 10.0
        parent_item.component.y = 20.0
        parent_item.setPos(10.0, 20.0)

        child_asset_item, child_asset = _make_asset(
            asset_type="window", group_bound=False,
        )
        child = Component(
            id="child",
            asset_id=child_asset.id,
            x=-20.0,
            y=-30.0,
            attach_to="parent",
            attach_anchor="bottom",
            parent_anchor="mp_endpoint__0__0",
        )
        child_item = ComponentItem(child, asset=child_asset)

        expected_parent = parent_item.mount_locations_local()["mp_endpoint"][0]
        parent_scene = parent_item.mapToScene(
            QPointF(expected_parent[3], expected_parent[4]),
        )
        child_endpoint = child_item.resolve_child_endpoint("bottom")
        expected_x = parent_scene.x() - child_endpoint["local_position"][0]
        expected_y = parent_scene.y() - child_endpoint["local_position"][1]

        changed = reflow_from(
            "parent",
            {"parent": parent_item, "child": child_item},
            _Composite({"child": child}),
        )

        self.assertEqual(changed, 1)
        self.assertAlmostEqual(child.x, expected_x)
        self.assertAlmostEqual(child.y, expected_y)

    def test_asset_snapshot_restore_preserves_group_bound_endpoint_for_undo_redo(self):
        original_item, original_asset = _make_asset(overrides={"height": 2.0})
        restored_asset = Asset.from_dict(original_asset.to_dict())
        component = Component(
            id="parent",
            asset_id=restored_asset.id,
            param_overrides={"height": 2.0},
        )
        item = ComponentItem(component, asset=restored_asset)
        before = item.mount_locations_local()["mp_endpoint"][0][3:]
        undo_snapshot = restored_asset.snapshot()

        restored_asset.layers[0].geometry["contour"][0] = [6.0, 2.0]
        restored_asset.parameters["p_height"].value = 1.0
        self.assertEqual(
            undo_snapshot["layers"][0]["geometry"]["contour"][0],
            [0.0, 0.0],
        )
        redo_snapshot = restored_asset.snapshot()
        item.prepareGeometryChange()
        item._rebuild_paths()
        after = item.mount_locations_local()["mp_endpoint"][0][3:]
        self.assertNotEqual(before, after)

        restored_asset.restore(undo_snapshot)
        item.set_asset(restored_asset)
        after_undo = item.mount_locations_local()["mp_endpoint"][0][3:]
        self.assertEqual(after_undo, before)

        restored_asset.restore(redo_snapshot)
        item.set_asset(restored_asset)
        after_redo = item.mount_locations_local()["mp_endpoint"][0][3:]
        self.assertEqual(after_redo, after)


if __name__ == "__main__":
    unittest.main()
