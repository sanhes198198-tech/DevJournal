import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

from app.constructor.constructor_window import ConstructorWindow
from app.constructor.reflow_engine import reflow_from
from app.constructor.snap_resolver import find_mount_snap
from app.constructor.view.items.component_item import ComponentItem
from app.vector_editor.model import Asset, Component
from app.vector_editor.model.mounting import MountPoint
from app.vector_editor.model.mounting.attachment import (
    endpoint_from_component_value,
)


class _ParentItem:
    def __init__(self, locations, offset=(10.0, 20.0)):
        self.locations = locations
        self.offset = offset
        self.mount_locations_calls = 0

    def mount_locations_local(self):
        self.mount_locations_calls += 1
        return self.locations

    def mapToScene(self, point):
        return QPointF(
            self.offset[0] + point.x(),
            self.offset[1] + point.y(),
        )


class _ChildItem:
    def __init__(self, local_position=(2.0, 3.0), resolved=True):
        self.local_position = local_position
        self.resolved = resolved
        self.aliases = []
        self.positions = []
        self.update_count = 0
        self.current_position = QPointF(4.0, 5.0)

    def resolve_child_endpoint(self, alias):
        self.aliases.append(alias)
        if not self.resolved:
            return {
                "local_position": None,
                "source": "legacy_anchor",
                "alias": alias,
                "resolved": False,
                "diagnostic": "unresolved",
            }
        return {
            "local_position": self.local_position,
            "source": "legacy_anchor",
            "alias": alias,
            "resolved": True,
            "diagnostic": None,
        }

    def setPos(self, x, y):
        self.current_position = QPointF(float(x), float(y))
        self.positions.append((x, y))

    def mapToScene(self, point):
        return self.current_position + point

    def position_for_endpoint_at_scene(self, local_position, scene_position):
        endpoint_scene = self.mapToScene(QPointF(*local_position))
        delta = scene_position - endpoint_scene
        return self.current_position + delta

    def update(self):
        self.update_count += 1


class _Composite:
    def __init__(self, child):
        self.child = child

    def get_component(self, component_id):
        return self.child if component_id == "child" else None


class _SnapComponentItem:
    def __init__(self, component_id, attach_to="", locations=()):
        self._component = SimpleNamespace(id=component_id, attach_to=attach_to)
        self._locations = list(locations)

    def mount_locations_by_role(self, role):
        self.role = role
        return self._locations


class _SnapScene:
    def __init__(self, items):
        self._items = items

    def items(self):
        return self._items


class Phase1DParentEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def _run_reflow(self, parent_anchor, *, locations=None, child_item=None):
        component = Component(
            id="child",
            attach_to="parent",
            attach_anchor="bottom",
            parent_anchor=parent_anchor,
            x=4.0,
            y=5.0,
        )
        parent_item = _ParentItem(
            locations or {
                "mp_parent": [(0, 0, None, 1.0, 2.0)],
            }
        )
        child_item = child_item or _ChildItem()
        changed = reflow_from(
            "parent",
            {"parent": parent_item, "child": child_item},
            _Composite(component),
        )
        return changed, component, parent_item, child_item

    def test_native_parent_tag_is_adapted_then_reflow_uses_matching_index(self):
        locations = {
            "mp_other": [(0, 0, None, 100.0, 100.0)],
            "mp_parent": [
                (0, 0, None, 1.0, 2.0),
                (1, 0, None, 11.0, 12.0),
                (0, 1, None, 21.0, 22.0),
            ],
        }
        with patch(
            "app.vector_editor.model.component.endpoint_from_component_value",
            wraps=endpoint_from_component_value,
        ) as classify, patch(
            "app.constructor.reflow_engine.endpoint_from_component_value",
            side_effect=AssertionError(
                "Reflow must read the unified native relation"
            ),
        ):
            changed, component, parent, child_item = self._run_reflow(
                "mp_parent__1__0", locations=locations,
            )

        classify.assert_called_once_with(
            "mp_parent__1__0", field="parent_anchor"
        )
        self.assertEqual(
            component.attachment.parent_location,
            {
                "mountpoint_id": "mp_parent",
                "index_x": 1,
                "index_y": 0,
            },
        )
        self.assertEqual(changed, 1)
        self.assertEqual(child_item.aliases, ["bottom"])
        self.assertEqual((component.x, component.y), (19.0, 29.0))
        self.assertEqual(parent.mount_locations_calls, 1)

    def test_unknown_mountpoint_does_not_move_child(self):
        changed, component, _parent, child_item = self._run_reflow(
            "mp_unknown__0__0"
        )

        self.assertEqual(changed, 0)
        self.assertEqual((component.x, component.y), (4.0, 5.0))
        self.assertEqual(child_item.positions, [])

    def test_invalid_location_index_does_not_move_child(self):
        changed, component, _parent, child_item = self._run_reflow(
            "mp_parent__8__3"
        )

        self.assertEqual(changed, 0)
        self.assertEqual((component.x, component.y), (4.0, 5.0))
        self.assertEqual(child_item.positions, [])

    def test_parent_legacy_aliases_are_skipped(self):
        for value in ("top", "bottom"):
            with self.subTest(parent_anchor=value):
                changed, component, parent, child_item = self._run_reflow(value)
                self.assertEqual(changed, 0)
                self.assertEqual((component.x, component.y), (4.0, 5.0))
                self.assertEqual(parent.mount_locations_calls, 0)
                self.assertEqual(child_item.aliases, [])

    def test_slot_parent_endpoint_is_skipped(self):
        changed, component, parent, child_item = self._run_reflow(
            "slot_g_4cb42e0a_0_0"
        )

        self.assertEqual(changed, 0)
        self.assertEqual((component.x, component.y), (4.0, 5.0))
        self.assertEqual(parent.mount_locations_calls, 0)
        self.assertEqual(child_item.aliases, [])

    def test_malformed_mountpoint_parent_tag_is_skipped(self):
        for value in ("mp_parent__x__0", "mp_parent__0__0__extra"):
            with self.subTest(parent_anchor=value):
                changed, component, parent, child_item = self._run_reflow(value)
                self.assertEqual(changed, 0)
                self.assertEqual((component.x, component.y), (4.0, 5.0))
                self.assertEqual(parent.mount_locations_calls, 0)
                self.assertEqual(child_item.aliases, [])

    def test_empty_parent_anchor_is_skipped(self):
        changed, component, parent, child_item = self._run_reflow("")

        self.assertEqual(changed, 0)
        self.assertEqual((component.x, component.y), (4.0, 5.0))
        self.assertEqual(parent.mount_locations_calls, 0)
        self.assertEqual(child_item.aliases, [])

    def test_relative_xy_parent_uses_mount_locations_local_path(self):
        geometry = {
            "contour": [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)],
            "closed": True,
            "units": "m",
            "node_ids": ["n0", "n1", "n2", "n3"],
            "groups": {},
            "extra_edges": [],
            "arcs": [],
            "extra_points": [],
            "extra_node_ids": [],
        }
        parent_asset = Asset(geometry=geometry)
        parent_asset.mountpoints = [
            MountPoint(
                id="mp_parent",
                position=(99.0, 99.0),
                anchor_mode="relative_xy",
                anchor_x=0.25,
                anchor_y=0.25,
            )
        ]
        parent_item = ComponentItem(
            Component(id="parent", asset_id=parent_asset.id),
            asset=parent_asset,
        )
        parent_item.setPos(20.0, 30.0)
        child_component = Component(
            id="child",
            attach_to="parent",
            attach_anchor="bottom",
            parent_anchor="mp_parent__0__0",
            x=0.0,
            y=0.0,
        )
        child_item = _ChildItem(local_position=(0.0, 0.0))

        changed = reflow_from(
            "parent",
            {"parent": parent_item, "child": child_item},
            _Composite(child_component),
        )

        self.assertEqual(changed, 1)
        self.assertAlmostEqual(child_component.x, 17.5)
        self.assertAlmostEqual(child_component.y, 32.5)

    def test_snap_result_parent_tag_format_is_unchanged(self):
        moving = _SnapComponentItem("child")
        parent = _SnapComponentItem(
            "parent",
            locations=[("mp_f7e3fca9", 2, 1, 10.0, 10.0)],
        )
        result = find_mount_snap(
            _SnapScene([moving, parent]),
            moving,
            (10.0, 10.0),
            "window",
            1.0,
            _SnapComponentItem,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.their_tag, "mp_f7e3fca9__2__1")
        self.assertEqual(
            result.their_location,
            {
                "mountpoint_id": "mp_f7e3fca9",
                "index_x": 2,
                "index_y": 1,
            },
        )

    def test_component_parent_anchor_serialization_is_unchanged(self):
        component = Component(
            id="child",
            asset_id="asset",
            attach_to="parent",
            attach_anchor="bottom",
            parent_anchor="mp_parent__1__0",
        )

        serialized = component.to_dict()
        restored = Component.from_dict(serialized)

        self.assertEqual(serialized["parent_anchor"], "mp_parent__1__0")
        self.assertEqual(restored.parent_anchor, "mp_parent__1__0")

    def test_slot_visibility_guard_still_skips_slot_attached_components(self):
        rule = SimpleNamespace(
            enabled=True,
            component_id="child",
            parameter_name="width",
            evaluate=lambda _value: True,
            action_for=lambda _component_id, _condition: "hide",
        )
        component = Component(
            id="child",
            param_overrides={"width": 2.0},
            parent_anchor="slot_g_4cb42e0a_0_0",
        )

        class VisibilityItem:
            def __init__(self):
                self.visible = True

            def isVisible(self):
                return self.visible

            def setVisible(self, visible):
                self.visible = visible

        item = VisibilityItem()
        composite = SimpleNamespace(
            visibility_rules={"rule": rule},
            get_component=lambda component_id: (
                component if component_id == "child" else None
            ),
        )
        window = SimpleNamespace(
            _current_composite=composite,
            _items_by_comp_id={"child": item},
            _registry=None,
        )

        ConstructorWindow._apply_visibility_rules(window)

        self.assertTrue(item.visible)


if __name__ == "__main__":
    unittest.main()
