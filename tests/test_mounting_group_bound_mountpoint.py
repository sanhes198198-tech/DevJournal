import unittest

from app.vector_editor.model import Asset
from app.vector_editor.model.mounting import Distribution, MountPoint


class MountPointGroupBindingTests(unittest.TestCase):
    def test_existing_static_mountpoint_payload_and_resolution_are_unchanged(self):
        mountpoint = MountPoint(
            id="mp_static",
            role="window",
            position=(2.5, -1.25),
            distribution=Distribution(),
        )

        self.assertFalse(mountpoint.is_group_bound())
        self.assertEqual(
            mountpoint.to_dict(),
            {
                "id": "mp_static",
                "role": "window",
                "position": [2.5, -1.25],
                "distribution": {
                    "count_x": 1,
                    "count_y": 1,
                    "spacing_x": 0.0,
                    "spacing_y": 0.0,
                },
            },
        )
        self.assertEqual(
            [location.position for location in mountpoint.resolve()],
            [(2.5, -1.25)],
        )

    def test_semantic_group_binding_is_separate_from_legacy_provenance(self):
        mountpoint = MountPoint(
            id="mp_group_bound",
            position=(8.0, 9.0),
            legacy_group_id="g_old_provenance",
            legacy_auto_rule={"axis": "x"},
            semantic_group_id="g_live_binding",
        )

        serialized = mountpoint.to_dict()
        self.assertTrue(mountpoint.is_group_bound())
        self.assertEqual(serialized["semantic_group_id"], "g_live_binding")
        self.assertEqual(serialized["legacy_group_id"], "g_old_provenance")
        self.assertEqual(
            serialized["legacy_auto_rule"], {"axis": "x"},
        )

        restored = MountPoint.from_dict(serialized)
        self.assertTrue(restored.is_group_bound())
        self.assertEqual(restored.semantic_group_id, "g_live_binding")
        self.assertEqual(restored.legacy_group_id, "g_old_provenance")
        self.assertEqual(
            restored.legacy_auto_rule, {"axis": "x"},
        )

    def test_group_bound_point_cannot_fall_back_to_saved_static_position(self):
        mountpoint = MountPoint(
            id="mp_group_bound",
            position=(8.0, 9.0),
            semantic_group_id="g_live_binding",
        )

        with self.assertRaisesRegex(ValueError, "Asset-aware resolution"):
            mountpoint.resolve()

    def test_legacy_group_id_alone_keeps_existing_static_behavior(self):
        mountpoint = MountPoint(
            id="mp_migrated_provenance",
            position=(3.0, 4.0),
            legacy_group_id="g_legacy_source",
            legacy_auto_rule={"count": 2},
        )

        self.assertFalse(mountpoint.is_group_bound())
        self.assertNotIn("semantic_group_id", mountpoint.to_dict())
        self.assertEqual(
            [location.position for location in mountpoint.resolve()],
            [(3.0, 4.0)],
        )

    def test_group_binding_round_trips_through_asset_persistence(self):
        asset = Asset(asset_id="asset_group_binding")
        asset.mountpoints = [
            MountPoint(
                id="mp_group_bound",
                position=(5.0, 6.0),
                semantic_group_id="g_anchor_bottom",
            ),
        ]

        payload = asset.to_dict()
        self.assertEqual(
            payload["mountpoints"][0]["semantic_group_id"],
            "g_anchor_bottom",
        )
        restored = Asset.from_dict(payload)
        self.assertEqual(
            restored.mountpoints[0].semantic_group_id,
            "g_anchor_bottom",
        )
        self.assertTrue(restored.mountpoints[0].is_group_bound())


if __name__ == "__main__":
    unittest.main()
