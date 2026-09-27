import unittest

from app.vector_editor.model.asset import Asset
from app.vector_editor.model.mounting import Attachment, Distribution, MountPoint
from app.vector_editor.model.parameter import Parameter, ParameterTarget
from app.vector_editor.model.semantic_group import SemanticGroup


class GroupBoundMountPointResolutionTests(unittest.TestCase):
    def make_asset(self):
        asset = Asset(
            asset_id="asset_group_bound_resolution",
            geometry={
                "contour": [[0.0, 0.0], [2.0, 0.0], [10.0, 4.0]],
                "closed": False,
                "units": "m",
                "node_ids": ["n0", "n1", "n2"],
                "groups": {},
                "extra_edges": [],
                "arcs": [],
                "extra_points": [],
                "extra_node_ids": [],
            },
            semantic_groups={
                "g_endpoint": SemanticGroup(
                    id="g_endpoint",
                    name="anchor_bottom",
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
                            "g_endpoint", koef_x=0.0, koef_y=1.0,
                        ),
                    ],
                ),
            },
        )
        asset.mountpoints = [
            MountPoint(
                id="mp_endpoint",
                position=(99.0, 99.0),
                semantic_group_id="g_endpoint",
            ),
        ]
        return asset

    @staticmethod
    def attachment(index_x=0, index_y=0):
        return Attachment(
            target_type="mountpoint",
            target_id="mp_endpoint",
            location={"x": index_x, "y": index_y},
        )

    def test_endpoint_tracks_current_group_geometry(self):
        asset = self.make_asset()
        attachment = self.attachment()

        initial_position, source = attachment.resolve(asset)
        self.assertEqual(source, "native_mountpoint")
        self.assertEqual(initial_position, (1.0, 0.0))

        asset.geometry["contour"][0] = [4.0, 2.0]
        updated_position, updated_source = attachment.resolve(asset)

        self.assertEqual(updated_source, "native_mountpoint")
        self.assertEqual(updated_position, (3.0, 1.0))
        self.assertEqual(asset.mountpoints[0].position, (99.0, 99.0))

    def test_parameter_overrides_shift_the_group_bound_endpoint(self):
        asset = self.make_asset()
        attachment = self.attachment()

        base_position, _ = attachment.resolve(asset)
        overridden_position, source = attachment.resolve(
            asset,
            param_overrides={"height": 2.5},
        )

        self.assertEqual(source, "native_mountpoint")
        self.assertEqual(base_position, (1.0, 0.0))
        self.assertEqual(overridden_position, (1.0, 2.5))
        self.assertEqual(
            asset.geometry["contour"],
            [[0.0, 0.0], [2.0, 0.0], [10.0, 4.0]],
        )

    def test_asset_round_trip_preserves_live_group_resolution(self):
        restored = Asset.from_dict(self.make_asset().to_dict())
        self.assertEqual(
            restored.mountpoints[0].semantic_group_id,
            "g_endpoint",
        )
        attachment = self.attachment()

        before, _ = attachment.resolve(restored)
        restored.layers[0].geometry["contour"][0] = [6.0, 0.0]
        after, source = attachment.resolve(restored)

        self.assertEqual(before, (1.0, 0.0))
        self.assertEqual(after, (4.0, 0.0))
        self.assertEqual(source, "native_mountpoint")

    def test_missing_group_does_not_fall_back_to_saved_position(self):
        asset = self.make_asset()
        asset.mountpoints[0].semantic_group_id = "g_missing"

        with self.assertRaisesRegex(ValueError, "Unknown or empty SemanticGroup"):
            self.attachment().resolve(asset)

    def test_group_bound_distribution_must_be_single_location(self):
        asset = self.make_asset()
        asset.mountpoints[0].distribution = Distribution(count_x=2)

        with self.assertRaisesRegex(ValueError, "single location"):
            self.attachment().resolve(asset)

    def test_group_bound_location_rejects_nonzero_index(self):
        asset = self.make_asset()

        with self.assertRaisesRegex(ValueError, "Invalid MountPoint location index"):
            self.attachment(index_x=1).resolve(asset)


if __name__ == "__main__":
    unittest.main()
