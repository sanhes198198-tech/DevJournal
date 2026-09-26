import math
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication, QGraphicsScene

from app.constructor.commands import MoveWithReflowCommand
from app.constructor.reflow_engine import reflow_from
from app.constructor.view.items.component_item import ComponentItem
from app.vector_editor.model import (
    Asset,
    Component,
    Parameter,
    ParameterTarget,
    SemanticGroup,
)
from app.vector_editor.model.mounting import Distribution, MountPoint, MountRole


_CONTOUR = [[0.0, 0.0], [8.0, 0.0], [8.0, 6.0], [0.0, 6.0]]
_NODE_IDS = ["n0", "n1", "n2", "n3"]


def _make_asset(
    asset_id,
    mountpoint_id,
    *,
    role=None,
    distribution=None,
    group_bound=False,
    asset_type="other",
):
    geometry = {
        "contour": [list(point) for point in _CONTOUR],
        "closed": True,
        "units": "m",
        "node_ids": list(_NODE_IDS),
        "groups": {},
        "extra_edges": [],
        "arcs": [],
        "extra_points": [],
        "extra_node_ids": [],
    }
    semantic_groups = {}
    parameters = {}
    semantic_group_id = None
    position = (6.5, 4.5)
    if group_bound:
        semantic_group_id = "g_endpoint"
        semantic_groups = {
            "g_endpoint": SemanticGroup(
                id="g_endpoint",
                name="mount_edge",
                node_ids=["n0", "n1"],
            ),
            "g_shift": SemanticGroup(
                id="g_shift",
                name="height_shift",
                node_ids=["n0", "n1"],
            ),
        }
        parameters = {
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
        }
        # The resolved location must come from the SemanticGroup centroid.
        position = (100.0, 100.0)

    asset = Asset(
        asset_id=asset_id,
        type_=asset_type,
        geometry=geometry,
        semantic_groups=semantic_groups,
        parameters=parameters,
    )
    asset.mountpoints = [
        MountPoint(
            id=mountpoint_id,
            role=role,
            position=position,
            distribution=distribution,
            semantic_group_id=semantic_group_id,
        ),
    ]
    return asset


class _Composite:
    def __init__(self, *components):
        self.components = {component.id: component for component in components}

    def get_component(self, component_id):
        return self.components.get(component_id)


class ChildTransformReflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def _make_pair(
        self,
        *,
        child_rotation=0.0,
        child_scale=1.0,
        parent_rotation=0.0,
        parent_scale=1.0,
        parent_group_bound=False,
        distribution=False,
        index=(0, 0),
    ):
        dist = (
            Distribution(
                count_x=2,
                count_y=2,
                spacing_x=2.5,
                spacing_y=1.75,
            )
            if distribution
            else None
        )
        parent_asset = _make_asset(
            "asset_parent",
            "mp_parent",
            role=MountRole.WINDOW,
            distribution=dist,
            group_bound=parent_group_bound,
        )
        child_asset = _make_asset(
            "asset_child",
            "mp_child",
            distribution=dist,
            asset_type="window",
        )
        parent_component = Component(
            id="parent",
            asset_id=parent_asset.id,
            x=13.0,
            y=-7.0,
            rotation=parent_rotation,
            scale=parent_scale,
            param_overrides=(
                {"height": 1.5} if parent_group_bound else None
            ),
        )
        child_component = Component(
            id="child",
            asset_id=child_asset.id,
            x=-31.0,
            y=17.0,
            rotation=child_rotation,
            scale=child_scale,
            attach_to="parent",
            attach_anchor=None,
            parent_location={
                "mountpoint_id": "mp_parent",
                "index_x": index[0],
                "index_y": index[1],
            },
            attach_location={
                "mountpoint_id": "mp_child",
                "index_x": index[0],
                "index_y": index[1],
            },
        )
        parent_item = ComponentItem(parent_component, asset=parent_asset)
        child_item = ComponentItem(child_component, asset=child_asset)
        composite = _Composite(parent_component, child_component)
        items = {"parent": parent_item, "child": child_item}
        return (
            parent_component,
            child_component,
            parent_item,
            child_item,
            composite,
            items,
        )

    @staticmethod
    def _target_scene(parent_item, location):
        rows = parent_item.mount_locations_local().get(
            location["mountpoint_id"], [],
        )
        row = next(
            row for row in rows
            if row[0] == location["index_x"]
            and row[1] == location["index_y"]
        )
        return parent_item.mapToScene(QPointF(row[3], row[4]))

    def _assert_aligned(
        self, parent_component, child_item, parent_item,
    ):
        parent_scene = self._target_scene(
            parent_item, parent_component.attachment and {
                "mountpoint_id": "mp_parent",
                "index_x": child_item.component.parent_location["index_x"],
                "index_y": child_item.component.parent_location["index_y"],
            },
        )
        endpoint = child_item.resolve_child_endpoint(None)
        self.assertTrue(endpoint["resolved"], endpoint["diagnostic"])
        child_scene = child_item.mapToScene(
            QPointF(*endpoint["local_position"])
        )
        distance = math.hypot(
            child_scene.x() - parent_scene.x(),
            child_scene.y() - parent_scene.y(),
        )
        self.assertLessEqual(distance, 1e-9)
        return distance

    def _run_reflow(self, **kwargs):
        (
            parent_component,
            _child_component,
            parent_item,
            child_item,
            composite,
            items,
        ) = self._make_pair(**kwargs)
        changed = reflow_from("parent", items, composite)
        self.assertGreater(changed, 0)
        self._assert_aligned(parent_component, child_item, parent_item)
        return (
            parent_component,
            child_item.component,
            parent_item,
            child_item,
            composite,
            items,
        )

    def test_a_to_i_transform_matrix_keeps_native_endpoints_aligned(self):
        cases = (
            ("A_identity", 0.0, 1.0, 0.0, 1.0),
            ("B_child_rotation", 37.0, 1.0, 0.0, 1.0),
            ("C_child_scale", 0.0, 1.65, 0.0, 1.0),
            ("D_child_rotation_and_scale", 41.0, 0.72, 0.0, 1.0),
            ("E_parent_rotation", 0.0, 1.0, 29.0, 1.0),
            ("F_parent_scale", 0.0, 1.0, 0.0, 1.45),
            ("G_parent_rotation_and_scale", 0.0, 1.0, -32.0, 1.3),
            ("H_both_rotations", 23.0, 1.0, -17.0, 1.0),
            ("I_both_scales", 0.0, 0.68, 0.0, 1.8),
        )
        for name, child_rotation, child_scale, parent_rotation, parent_scale in cases:
            with self.subTest(case=name):
                self._run_reflow(
                    child_rotation=child_rotation,
                    child_scale=child_scale,
                    parent_rotation=parent_rotation,
                    parent_scale=parent_scale,
                )

    def test_j_group_bound_mountpoint_and_parameter_override(self):
        self._run_reflow(
            child_rotation=28.0,
            child_scale=1.2,
            parent_rotation=-19.0,
            parent_scale=0.9,
            parent_group_bound=True,
        )

    def test_k_nonzero_distribution_index_on_both_endpoints(self):
        self._run_reflow(
            child_rotation=13.0,
            child_scale=0.83,
            parent_rotation=26.0,
            parent_scale=1.4,
            distribution=True,
            index=(1, 1),
        )

    def test_l_reflow_after_parent_transform_changes(self):
        (
            parent_component,
            _child_component,
            parent_item,
            child_item,
            composite,
            items,
        ) = self._make_pair(
            child_rotation=35.0,
            child_scale=0.76,
        )
        self.assertGreater(reflow_from("parent", items, composite), 0)
        self._assert_aligned(parent_component, child_item, parent_item)

        parent_component.rotation = -38.0
        parent_component.scale = 1.55
        parent_item.apply_from_component()
        self.assertGreater(reflow_from("parent", items, composite), 0)
        self._assert_aligned(parent_component, child_item, parent_item)

    def test_m_undo_redo_preserves_transformed_endpoint_alignment(self):
        (
            parent_component,
            child_component,
            parent_item,
            child_item,
            composite,
            items,
        ) = self._make_pair(
            child_rotation=27.0,
            child_scale=1.25,
            parent_rotation=-16.0,
            parent_scale=0.87,
        )
        self.assertGreater(reflow_from("parent", items, composite), 0)
        before = {
            "parent": (parent_component.x, parent_component.y),
            "child": (child_component.x, child_component.y),
        }

        parent_component.x += 9.0
        parent_component.y -= 4.0
        parent_item.apply_from_component()
        self.assertGreater(reflow_from("parent", items, composite), 0)
        after = {
            "parent": (parent_component.x, parent_component.y),
            "child": (child_component.x, child_component.y),
        }
        command = MoveWithReflowCommand(before, after, items, composite)

        command.undo()
        self._assert_aligned(parent_component, child_item, parent_item)
        command.redo()
        self._assert_aligned(parent_component, child_item, parent_item)

    def test_snap_uses_the_same_scene_endpoint_positioning_as_reflow(self):
        parent_asset = _make_asset(
            "asset_snap_parent",
            "mp_parent_snap",
            role=MountRole.WINDOW,
            asset_type="other",
        )
        child_asset = _make_asset(
            "asset_snap_child",
            "mp_child_snap",
            asset_type="window",
        )
        parent_asset.mountpoints[0].position = (6.5, 4.5)
        child_asset.mountpoints[0].position = (7.0, 5.0)
        parent_component = Component(
            id="snap_parent",
            asset_id=parent_asset.id,
            x=4.0,
            y=-3.0,
            rotation=24.0,
            scale=1.35,
        )
        child_component = Component(
            id="snap_child",
            asset_id=child_asset.id,
            rotation=-31.0,
            scale=0.74,
            role=MountRole.WINDOW,
            attach_location={
                "mountpoint_id": "mp_child_snap",
                "index_x": 0,
                "index_y": 0,
            },
        )
        parent_item = ComponentItem(parent_component, asset=parent_asset)
        child_item = ComponentItem(child_component, asset=child_asset)
        scene = QGraphicsScene()
        scene.addItem(parent_item)
        scene.addItem(child_item)

        parent_location = parent_item.mount_locations_world()[
            "mp_parent_snap"
        ][0]
        target = QPointF(parent_location[3], parent_location[4])
        endpoint = child_item.resolve_child_endpoint(None)
        current = child_item.mapToScene(
            QPointF(*endpoint["local_position"])
        )
        # Place the transformed child endpoint within Snap's threshold.
        child_item.setPos(
            child_item.pos().x() + target.x() - current.x() + 0.2,
            child_item.pos().y() + target.y() - current.y() - 0.1,
        )

        child_item._try_snap()

        endpoint = child_item.resolve_child_endpoint(None)
        child_scene = child_item.mapToScene(
            QPointF(*endpoint["local_position"])
        )
        self.assertLessEqual(
            math.hypot(
                child_scene.x() - target.x(),
                child_scene.y() - target.y(),
            ),
            1e-9,
        )


if __name__ == "__main__":
    unittest.main()
