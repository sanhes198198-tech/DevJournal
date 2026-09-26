import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication, QGraphicsScene

from app.constructor.reflow_engine import reflow_from
from app.constructor.view.items.component_item import ComponentItem
from app.vector_editor.model import (
    Asset,
    Component,
    Parameter,
    ParameterTarget,
    SemanticGroup,
)


def _child_item(*, overrides=None):
    points = {
        "n0": (0.0, 0.0),
        "n1": (2.0, 0.0),
        "n2": (10.0, 4.0),
    }
    geometry = {
        "contour": list(points.values()),
        "closed": False,
        "units": "m",
        "node_ids": list(points),
        "groups": {},
        "extra_edges": [],
        "arcs": [],
        "extra_points": [],
        "extra_node_ids": [],
    }
    groups = {
        "g_anchor": SemanticGroup(
            id="g_anchor", name="anchor_bottom", node_ids=["n0", "n1"],
        ),
        "g_shift": SemanticGroup(
            id="g_shift", name="shift", node_ids=["n0", "n1"],
        ),
    }
    asset = Asset(
        type_="other",
        geometry=geometry,
        semantic_groups=groups,
        parameters={
            "width": Parameter(
                name="width",
                value=0.0,
                targets=[ParameterTarget("g_shift", koef_x=1.0)],
            )
        },
    )
    component = Component(
        id="child",
        asset_id=asset.id,
        x=0.0,
        y=0.0,
        param_overrides=overrides,
        attach_to="parent",
        attach_anchor="bottom",
        parent_anchor="mp_parent__0__0",
    )
    return ComponentItem(component, asset=asset)


class _ParentItem:
    def mount_locations_local(self):
        return {"mp_parent": [(0, 0, None, 0.0, 0.0)]}

    def mapToScene(self, point):
        return QPointF(10.0 + point.x(), 20.0 + point.y())


class _Composite:
    def __init__(self, components):
        self.components = components

    def get_component(self, component_id):
        return self.components.get(component_id)


class Phase1CChildEndpointRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_snap_uses_child_resolver_and_maps_local_to_scene(self):
        asset = Asset(type_="window")
        item = ComponentItem(
            Component(id="moving", asset_id=asset.id, role="window"),
            asset=asset,
        )
        scene = QGraphicsScene()
        scene.addItem(item)
        item.setPos(10.0, 20.0)

        with (
            patch.object(
                item,
                "resolve_child_endpoint",
                return_value={
                    "local_position": (2.0, 3.0),
                    "source": "legacy_anchor",
                    "alias": "bottom",
                    "resolved": True,
                    "diagnostic": None,
                },
            ) as resolve,
            patch(
                "app.constructor.snap_resolver.find_mount_snap",
                return_value=None,
            ) as find_snap,
        ):
            item._try_snap()

        resolve.assert_called_once_with("bottom")
        self.assertEqual(find_snap.call_args.args[2], (12.0, 23.0))

    def test_reflow_uses_resolver_and_parameter_override_position(self):
        child_item = _child_item(overrides={"width": 1.0})
        component = child_item.component
        parent_item = _ParentItem()
        composite = _Composite({"child": component})
        resolver = child_item.resolve_child_endpoint

        with patch.object(
            child_item, "resolve_child_endpoint", wraps=resolver,
        ) as resolve:
            changed = reflow_from(
                "parent",
                {"parent": parent_item, "child": child_item},
                composite,
            )

        resolve.assert_called_once_with("bottom")
        self.assertEqual(changed, 1)
        self.assertAlmostEqual(component.x, 13.0)
        self.assertAlmostEqual(component.y, 22.0)

    def test_unresolved_child_endpoint_leaves_reflow_position_unchanged(self):
        component = Component(
            id="child",
            attach_to="parent",
            attach_anchor="missing",
            parent_anchor="mp_parent__0__0",
            x=4.0,
            y=5.0,
        )

        class UnresolvedChildItem:
            def __init__(self):
                self.resolve_child_endpoint = unittest.mock.Mock(
                    return_value={
                        "local_position": None,
                        "source": "legacy_anchor",
                        "alias": "missing",
                        "resolved": False,
                        "diagnostic": "Unknown legacy anchor alias",
                    }
                )

            def setPos(self, *_args):
                raise AssertionError("unresolved endpoint must not move item")

            def update(self):
                raise AssertionError("unresolved endpoint must not update item")

        child_item = UnresolvedChildItem()
        changed = reflow_from(
            "parent",
            {"parent": _ParentItem(), "child": child_item},
            _Composite({"child": component}),
        )

        child_item.resolve_child_endpoint.assert_called_once_with("missing")
        self.assertEqual(changed, 0)
        self.assertEqual((component.x, component.y), (4.0, 5.0))

    def test_component_attachment_serialization_keeps_existing_fields(self):
        component = Component(
            id="child",
            asset_id="asset",
            attach_to="parent",
            attach_anchor="bottom",
            parent_anchor="mp_parent__1__0",
        )

        serialized = component.to_dict()
        restored = Component.from_dict(serialized)

        self.assertEqual(serialized["attach_to"], "parent")
        self.assertEqual(serialized["attach_anchor"], "bottom")
        self.assertEqual(serialized["parent_anchor"], "mp_parent__1__0")
        self.assertEqual(restored.attach_to, "parent")
        self.assertEqual(restored.attach_anchor, "bottom")
        self.assertEqual(restored.parent_anchor, "mp_parent__1__0")


if __name__ == "__main__":
    unittest.main()
