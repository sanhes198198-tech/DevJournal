import copy
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF
from PySide6.QtWidgets import (
    QApplication, QGraphicsScene, QGraphicsSceneMouseEvent,
)

from app.constructor.reflow_engine import reflow_from
from app.constructor.view.items.component_item import ComponentItem
from app.vector_editor.model import Asset, Component, SemanticGroup
from app.vector_editor.model.mounting import MountPoint


ASSET_DIR = Path(__file__).resolve().parents[1] / "app" / "vector_editor" / "assets"


def _make_asset(
    asset_id,
    *,
    type_="other",
    group_id="g_endpoint",
    group_name="anchor_bottom",
    mountpoint_id="mp_endpoint",
    role=None,
    group_bound=True,
):
    points = {
        "n0": (2.0, 2.0),
        "n1": (4.0, 2.0),
        "n2": (0.0, 0.0),
        "n3": (10.0, 10.0),
    }
    geometry = {
        "contour": [list(point) for point in points.values()],
        "closed": False,
        "units": "m",
        "node_ids": list(points),
        "groups": {},
        "extra_edges": [],
        "arcs": [],
        "extra_points": [],
        "extra_node_ids": [],
    }
    asset = Asset(
        asset_id=asset_id,
        type_=type_,
        geometry=geometry,
        semantic_groups={
            group_id: SemanticGroup(
                id=group_id,
                name=group_name,
                node_ids=["n0", "n1"],
            ),
        },
    )
    if group_bound:
        asset.mountpoints = [
            MountPoint(
                id=mountpoint_id,
                role=role,
                position=(3.0, 2.0),
                semantic_group_id=group_id,
            ),
        ]
    return asset


class _Composite:
    def __init__(self, components):
        self.components = components

    def get_component(self, component_id):
        return self.components.get(component_id)


class Phase2AChildEndpointMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_all_real_child_links_resolve_natively_without_legacy_alias(self):
        count = 0
        pairs = set()
        saw_overrides = False

        for composite_path in sorted(ASSET_DIR.glob("*.json")):
            composite_data = json.loads(
                composite_path.read_text(encoding="utf-8")
            )
            for component_id, component_data in (
                composite_data.get("components") or {}
            ).items():
                address = component_data.get("attach_location")
                if not address:
                    continue

                self.assertIsNone(component_data.get("attach_anchor"))
                count += 1
                saw_overrides = saw_overrides or bool(
                    component_data.get("param_overrides")
                )
                self.assertEqual(
                    set(address),
                    {"mountpoint_id", "index_x", "index_y"},
                    f"{composite_path.name}:{component_id}",
                )
                self.assertEqual(address["index_x"], 0)
                self.assertEqual(address["index_y"], 0)

                child_id = component_data["asset_id"]
                child_path = ASSET_DIR / f"{child_id}.json"
                child_data = json.loads(child_path.read_text(encoding="utf-8"))
                child_asset = Asset.from_dict(child_data)
                component = Component.from_dict(component_data)
                self.assertIsNone(component.attach_anchor)
                item = ComponentItem(component, asset=child_asset)

                with patch.object(
                    item,
                    "anchors_local",
                    side_effect=AssertionError(
                        "native child endpoint used legacy anchors_local"
                    ),
                ):
                    endpoint = item.resolve_child_endpoint(None)
                self.assertTrue(endpoint["resolved"], endpoint["diagnostic"])
                self.assertEqual(endpoint["source"], "native_mountpoint")
                self.assertIsNone(endpoint["alias"])
                self.assertEqual(
                    endpoint["mountpoint_id"],
                    address["mountpoint_id"],
                )

                mountpoint = next(
                    mp for mp in child_asset.mountpoints
                    if mp.id == endpoint["mountpoint_id"]
                )
                self.assertTrue(mountpoint.is_group_bound())
                self.assertIsNone(mountpoint.role)
                self.assertEqual(
                    mountpoint.distribution.total_count(), 1,
                )
                native_locations = item.mount_locations_local()[mountpoint.id]
                native_local = next(
                    (lx, ly)
                    for ix, iy, _role, lx, ly in native_locations
                    if ix == address["index_x"]
                    and iy == address["index_y"]
                )
                self.assertEqual(endpoint["local_position"], native_local)
                pairs.add((child_id, address["mountpoint_id"]))

        self.assertEqual(count, 27)
        self.assertEqual(len(pairs), 9)
        self.assertTrue(saw_overrides)

    def test_all_27_links_load_save_and_resolve_without_legacy_alias(self):
        count = 0

        for composite_path in sorted(ASSET_DIR.glob("*.json")):
            original_data = json.loads(
                composite_path.read_text(encoding="utf-8")
            )
            native_only_data = copy.deepcopy(original_data)
            migrated_ids = []
            for component_id, record in (
                native_only_data.get("components") or {}
            ).items():
                if record.get("attach_location"):
                    self.assertIn(
                        record.get("attach_anchor"), (None, ""),
                    )
                    migrated_ids.append(component_id)
                    record["attach_anchor"] = None

            if not migrated_ids:
                continue

            loaded_composite = Asset.from_dict(native_only_data)
            saved_composite = loaded_composite.to_dict()
            restored_composite = Asset.from_dict(saved_composite)

            for component_id in migrated_ids:
                original_record = original_data["components"][component_id]
                child_data = json.loads(
                    (ASSET_DIR / f"{original_record['asset_id']}.json")
                    .read_text(encoding="utf-8")
                )
                child_asset = Asset.from_dict(child_data)

                component = restored_composite.get_component(component_id)
                self.assertIsNone(component.attach_anchor)
                location_before = copy.deepcopy(component.attach_location)
                self.assertEqual(component.attach_location, location_before)

                native_item = ComponentItem(component, asset=child_asset)
                with patch.object(
                    native_item,
                    "anchors_local",
                    side_effect=AssertionError(
                        "native child endpoint used legacy anchors_local"
                    ),
                ):
                    endpoint = native_item.resolve_child_endpoint(None)

                self.assertIsNotNone(endpoint)
                self.assertTrue(endpoint["resolved"], endpoint["diagnostic"])
                self.assertEqual(endpoint["source"], "native_mountpoint")
                self.assertIsNone(endpoint["alias"])
                native_locations = native_item.mount_locations_local()[
                    location_before["mountpoint_id"]
                ]
                native_local = next(
                    (lx, ly)
                    for ix, iy, _role, lx, ly in native_locations
                    if ix == location_before["index_x"]
                    and iy == location_before["index_y"]
                )
                self.assertAlmostEqual(
                    endpoint["local_position"][0], native_local[0],
                )
                self.assertAlmostEqual(
                    endpoint["local_position"][1], native_local[1],
                )
                count += 1

        self.assertEqual(count, 27)

    def test_native_endpoint_follows_geometry_and_snapshots_without_alias(self):
        asset = Asset.from_dict(_make_asset("native_no_alias_geometry").to_dict())
        component = Component(
            asset_id=asset.id,
            attach_location={
                "mountpoint_id": "mp_endpoint",
                "index_x": 0,
                "index_y": 0,
            },
        )
        component.attach_anchor = None
        item = ComponentItem(component, asset=asset)
        with patch.object(
            item,
            "anchors_local",
            side_effect=AssertionError("native endpoint used legacy anchors"),
        ):
            before = item.resolve_child_endpoint(None)["local_position"]
        undo_snapshot = asset.snapshot()

        asset.layers[0].geometry["contour"][0][1] += 2.0
        asset.layers[0].geometry["contour"][1][1] += 2.0
        redo_snapshot = asset.snapshot()
        item.prepareGeometryChange()
        item._rebuild_paths()
        with patch.object(
            item,
            "anchors_local",
            side_effect=AssertionError("native endpoint used legacy anchors"),
        ):
            after = item.resolve_child_endpoint(None)["local_position"]
        self.assertNotEqual(before, after)

        asset.restore(undo_snapshot)
        item.set_asset(asset)
        with patch.object(
            item,
            "anchors_local",
            side_effect=AssertionError("native endpoint used legacy anchors"),
        ):
            self.assertEqual(
                item.resolve_child_endpoint(None)["local_position"], before,
            )

        asset.restore(redo_snapshot)
        item.set_asset(asset)
        with patch.object(
            item,
            "anchors_local",
            side_effect=AssertionError("native endpoint used legacy anchors"),
        ):
            self.assertEqual(
                item.resolve_child_endpoint(None)["local_position"], after,
            )

    def test_unmigrated_component_still_uses_legacy_fallback(self):
        asset = _make_asset(
            "legacy_fallback",
            group_bound=False,
        )
        item = ComponentItem(
            Component(asset_id=asset.id, attach_anchor="bottom"),
            asset=asset,
        )
        resolver = item.anchors_local

        with patch.object(item, "anchors_local", wraps=resolver) as anchors:
            endpoint = item.resolve_child_endpoint("bottom")

        self.assertEqual(endpoint["source"], "legacy_anchor")
        self.assertTrue(endpoint["resolved"])
        anchors.assert_called_once_with()

    def test_component_and_asset_round_trip_preserve_native_child_address(self):
        composite_data = json.loads(
            (ASSET_DIR / "0f4b28549173.json").read_text(encoding="utf-8")
        )
        source = next(
            value for value in composite_data["components"].values()
            if value.get("attach_location")
        )
        composite = Asset.from_dict(composite_data)
        restored = Asset.from_dict(composite.to_dict())
        component = restored.get_component(source["id"])
        self.assertIsNone(component.attach_anchor)
        self.assertEqual(component.attach_location, source["attach_location"])
        self.assertEqual(
            component.to_dict()["attach_location"], source["attach_location"],
        )

        child_data = json.loads(
            (ASSET_DIR / f"{source['asset_id']}.json").read_text(encoding="utf-8")
        )
        child = Asset.from_dict(child_data)
        child_round_trip = Asset.from_dict(child.to_dict())
        mountpoint_id = source["attach_location"]["mountpoint_id"]
        mountpoint = next(
            mp for mp in child_round_trip.mountpoints if mp.id == mountpoint_id
        )
        self.assertTrue(mountpoint.is_group_bound())

    def test_native_set_attachment_writes_location_without_changing_alias(self):
        address = {
            "mountpoint_id": "mp_endpoint",
            "index_x": 0,
            "index_y": 0,
        }
        component = Component(attach_anchor="bottom")

        component.set_attachment(
            "new_parent",
            None,
            "mp_parent__0__0",
            attach_location=address,
        )

        self.assertEqual(component.attach_location, address)
        self.assertEqual(component.attach_anchor, "bottom")

    def test_group_bound_child_endpoint_tracks_geometry_through_undo_redo(self):
        asset = _make_asset("child_dynamic")
        asset = Asset.from_dict(asset.to_dict())
        component = Component(
            asset_id=asset.id,
            attach_anchor="bottom",
            attach_location={
                "mountpoint_id": "mp_endpoint",
                "index_x": 0,
                "index_y": 0,
            },
        )
        item = ComponentItem(component, asset=asset)
        before = item.resolve_child_endpoint("bottom")["local_position"]
        undo_snapshot = asset.snapshot()

        asset.layers[0].geometry["contour"][0][1] += 2.0
        asset.layers[0].geometry["contour"][1][1] += 2.0
        redo_snapshot = asset.snapshot()
        item.prepareGeometryChange()
        item._rebuild_paths()
        after = item.resolve_child_endpoint("bottom")["local_position"]
        self.assertNotEqual(before, after)

        asset.restore(undo_snapshot)
        item.set_asset(asset)
        self.assertEqual(
            item.resolve_child_endpoint("bottom")["local_position"], before,
        )

        asset.restore(redo_snapshot)
        item.set_asset(asset)
        self.assertEqual(
            item.resolve_child_endpoint("bottom")["local_position"], after,
        )

    def test_native_child_location_resolves_without_legacy_alias(self):
        asset = _make_asset("child_without_legacy_alias")
        component = Component(
            asset_id=asset.id,
            attach_location={
                "mountpoint_id": "mp_endpoint",
                "index_x": 0,
                "index_y": 0,
            },
        )
        item = ComponentItem(component, asset=asset)

        endpoint = item.resolve_child_endpoint("")

        self.assertTrue(endpoint["resolved"])
        self.assertEqual(endpoint["source"], "native_mountpoint")
        self.assertIsNotNone(endpoint["local_position"])

    def test_native_snap_carries_location_instead_of_legacy_child_tag(self):
        parent_asset = _make_asset(
            "snap_parent",
            group_id="g_parent",
            group_name="ordinary",
            mountpoint_id="mp_parent",
            role="window",
            group_bound=False,
        )
        parent_asset.mountpoints = [
            MountPoint(id="mp_parent", role="window", position=(3.0, 2.0)),
        ]
        parent_item = ComponentItem(
            Component(id="parent", asset_id=parent_asset.id),
            asset=parent_asset,
        )
        child_asset = _make_asset(
            "snap_child",
            type_="window",
            group_id="g_top",
            group_name="anchor_top",
            mountpoint_id="mp_child_top",
        )
        component = Component(
            id="child",
            asset_id=child_asset.id,
            role="window",
            attach_anchor="top",
            attach_location={
                "mountpoint_id": "mp_child_top",
                "index_x": 0,
                "index_y": 0,
            },
        )
        child_item = ComponentItem(component, asset=child_asset)
        scene = QGraphicsScene()
        scene.addItem(parent_item)
        scene.addItem(child_item)

        with patch.object(
            child_item,
            "anchors_local",
            side_effect=AssertionError("native snap used legacy anchors"),
        ):
            child_item._try_snap()

        self.assertEqual(
            child_item._pending_snap,
            (
                "parent",
                None,
                "mp_parent__0__0",
                {
                    "mountpoint_id": "mp_child_top",
                    "index_x": 0,
                    "index_y": 0,
                },
                {
                    "mountpoint_id": "mp_parent",
                    "index_x": 0,
                    "index_y": 0,
                },
            ),
        )
        child_item.mouseReleaseEvent(
            QGraphicsSceneMouseEvent(QEvent.Type.GraphicsSceneMouseRelease)
        )
        self.assertEqual(component.attach_to, "parent")
        self.assertEqual(component.attach_anchor, "top")
        self.assertEqual(component.parent_anchor, "")
        self.assertEqual(
            component.parent_location,
            {"mountpoint_id": "mp_parent", "index_x": 0, "index_y": 0},
        )
        self.assertEqual(
            component.attach_location,
            {
                "mountpoint_id": "mp_child_top",
                "index_x": 0,
                "index_y": 0,
            },
        )

    def test_snap_uses_native_location_when_attach_anchor_is_none(self):
        parent_asset = _make_asset(
            "native_snap_parent",
            group_id="g_parent",
            group_name="ordinary",
            group_bound=False,
        )
        parent_asset.mountpoints = [
            MountPoint(id="mp_parent", role="window", position=(3.0, 2.0)),
        ]
        parent_item = ComponentItem(
            Component(id="native_parent", asset_id=parent_asset.id),
            asset=parent_asset,
        )
        child_asset = _make_asset(
            "native_snap_child",
            type_="window",
            group_id="g_top",
            group_name="anchor_top",
            mountpoint_id="mp_child_top",
        )
        component = Component(
            id="native_child",
            asset_id=child_asset.id,
            role="window",
            attach_location={
                "mountpoint_id": "mp_child_top",
                "index_x": 0,
                "index_y": 0,
            },
        )
        component.attach_anchor = None
        child_item = ComponentItem(component, asset=child_asset)
        scene = QGraphicsScene()
        scene.addItem(parent_item)
        scene.addItem(child_item)

        with patch.object(
            child_item,
            "anchors_local",
            side_effect=AssertionError("native snap used legacy anchors"),
        ):
            child_item._try_snap()

        self.assertEqual(
            child_item._pending_snap,
            (
                "native_parent",
                None,
                "mp_parent__0__0",
                {
                    "mountpoint_id": "mp_child_top",
                    "index_x": 0,
                    "index_y": 0,
                },
                {
                    "mountpoint_id": "mp_parent",
                    "index_x": 0,
                    "index_y": 0,
                },
            ),
        )

        child_item.mouseReleaseEvent(
            QGraphicsSceneMouseEvent(QEvent.Type.GraphicsSceneMouseRelease)
        )
        self.assertEqual(component.attach_to, "native_parent")
        self.assertIsNone(component.attach_anchor)
        self.assertEqual(component.parent_anchor, "")
        self.assertEqual(
            component.parent_location,
            {"mountpoint_id": "mp_parent", "index_x": 0, "index_y": 0},
        )
        self.assertEqual(
            component.attach_location,
            {
                "mountpoint_id": "mp_child_top",
                "index_x": 0,
                "index_y": 0,
            },
        )

        restored = Component.from_dict(component.to_dict())
        self.assertIsNone(restored.attach_anchor)
        self.assertEqual(restored.attach_location, component.attach_location)
        restored_item = ComponentItem(restored, asset=child_asset)
        with patch.object(
            restored_item,
            "anchors_local",
            side_effect=AssertionError("saved native snap used legacy anchors"),
        ):
            endpoint = restored_item.resolve_child_endpoint(None)
        self.assertTrue(endpoint["resolved"], endpoint["diagnostic"])
        self.assertEqual(
            restored.parent_location,
            {"mountpoint_id": "mp_parent", "index_x": 0, "index_y": 0},
        )

    def test_legacy_snap_keeps_alias_and_does_not_create_native_location(self):
        parent_asset = _make_asset(
            "legacy_snap_parent",
            group_id="g_parent",
            group_name="ordinary",
            group_bound=False,
        )
        parent_asset.mountpoints = [
            MountPoint(id="mp_parent", role="window", position=(3.0, 2.0)),
        ]
        parent_item = ComponentItem(
            Component(id="legacy_parent", asset_id=parent_asset.id),
            asset=parent_asset,
        )
        child_asset = _make_asset(
            "legacy_snap_child",
            type_="window",
            group_id="g_bottom",
            group_name="anchor_bottom",
            group_bound=False,
        )
        component = Component(
            id="legacy_child",
            asset_id=child_asset.id,
            role="window",
            attach_anchor="bottom",
        )
        child_item = ComponentItem(component, asset=child_asset)
        scene = QGraphicsScene()
        scene.addItem(parent_item)
        scene.addItem(child_item)

        child_item._try_snap()
        self.assertEqual(
            child_item._pending_snap,
            (
                "legacy_parent",
                "bottom",
                "mp_parent__0__0",
                None,
                {"mountpoint_id": "mp_parent", "index_x": 0, "index_y": 0},
            ),
        )
        child_item.mouseReleaseEvent(
            QGraphicsSceneMouseEvent(QEvent.Type.GraphicsSceneMouseRelease)
        )
        self.assertEqual(component.attach_anchor, "bottom")
        self.assertIsNone(component.attach_location)
        self.assertEqual(component.parent_anchor, "")
        self.assertEqual(
            component.parent_location,
            {"mountpoint_id": "mp_parent", "index_x": 0, "index_y": 0},
        )

    def test_reflow_uses_native_child_location_without_legacy_alias(self):
        parent_asset = _make_asset(
            "reflow_parent",
            group_id="g_parent",
            group_name="ordinary",
            mountpoint_id="mp_parent",
            group_bound=False,
        )
        parent_asset.mountpoints = [
            MountPoint(id="mp_parent", position=(3.0, 2.0)),
        ]
        parent = ComponentItem(
            Component(id="parent", asset_id=parent_asset.id),
            asset=parent_asset,
        )
        parent.setPos(10.0, 20.0)

        child_asset = _make_asset("reflow_child")
        child = Component(
            id="child",
            asset_id=child_asset.id,
            x=-30.0,
            y=-40.0,
            attach_to="parent",
            parent_anchor="mp_parent__0__0",
            attach_location={
                "mountpoint_id": "mp_endpoint",
                "index_x": 0,
                "index_y": 0,
            },
        )
        child.attach_anchor = None
        child = Component.from_dict(child.to_dict())
        self.assertIsNone(child.attach_anchor)
        child_item = ComponentItem(child, asset=child_asset)
        parent_local = parent.mount_locations_local()["mp_parent"][0]
        parent_scene = parent.mapToScene(
            QPointF(parent_local[3], parent_local[4]),
        )
        with patch.object(
            child_item,
            "anchors_local",
            side_effect=AssertionError("native reflow used legacy anchors"),
        ), patch.object(
            child_item,
            "resolve_child_endpoint",
            wraps=child_item.resolve_child_endpoint,
        ) as resolve_endpoint:
            child_local = child_item.resolve_child_endpoint(None)["local_position"]
            expected = (
                parent_scene.x() - child_local[0],
                parent_scene.y() - child_local[1],
            )

            changed = reflow_from(
                "parent",
                {"parent": parent, "child": child_item},
                _Composite({"child": child}),
            )

        self.assertEqual(changed, 1)
        resolve_endpoint.assert_any_call(None)
        self.assertEqual((child.x, child.y), expected)
        self.assertEqual(
            child_item.resolve_child_endpoint(None)["source"],
            "native_mountpoint",
        )

    def test_ambiguous_unreferenced_asset_is_not_given_group_bound_points(self):
        ambiguous_path = ASSET_DIR / "9c545d9ccbfa.json"
        data = json.loads(ambiguous_path.read_text(encoding="utf-8"))
        duplicate_count = sum(
            1 for group in (data.get("semantic_groups") or {}).values()
            if group.get("name") == "anchor_bottom"
        )
        self.assertGreater(duplicate_count, 1)
        asset = Asset.from_dict(data)
        self.assertFalse(
            any(mp.semantic_group_id for mp in asset.mountpoints),
        )


if __name__ == "__main__":
    unittest.main()
