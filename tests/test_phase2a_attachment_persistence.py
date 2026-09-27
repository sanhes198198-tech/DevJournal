import json
import unittest
from pathlib import Path

from app.vector_editor.model import Asset, Component, SemanticGroup
from app.vector_editor.model.mounting import (
    Distribution,
    MountPoint,
    MountRole,
)


ASSET_DIR = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "vector_editor"
    / "assets"
)


class Phase2AAttachmentPersistenceTests(unittest.TestCase):
    @staticmethod
    def _json_round_trip(payload):
        """Exercise the same JSON-compatible boundary used by persistence."""
        return json.loads(json.dumps(payload))

    def test_composite_round_trip_preserves_native_and_legacy_child_paths(self):
        native_address = {
            "mountpoint_id": "mp_child_native",
            "index_x": 2,
            "index_y": 1,
        }
        native = Component(
            id="c_native",
            asset_id="asset_child_native",
            attach_to="c_parent",
            attach_anchor=None,
            parent_anchor="mp_parent__0__0",
            attach_location=native_address,
        )
        legacy = Component(
            id="c_legacy",
            asset_id="asset_child_legacy",
            attach_to="c_parent",
            attach_anchor="bottom",
            parent_anchor="top",
        )

        composite = Asset(
            asset_id="asset_composite_round_trip",
            components={native.id: native, legacy.id: legacy},
            semantic_groups={
                "g_mount": SemanticGroup(
                    id="g_mount",
                    name="mount_group",
                    node_ids=["n0", "n1"],
                ),
            },
        )
        composite.mountpoints = [
            MountPoint(
                id="mp_relative_grid",
                role=MountRole.WINDOW,
                position=(4.0, 5.0),
                distribution=Distribution(
                    count_x=2,
                    count_y=1,
                    spacing_x=3.5,
                ),
                anchor_mode="relative_xy",
                anchor_x=0.25,
                anchor_y=0.75,
            ),
            MountPoint(
                id="mp_group_bound",
                position=(6.0, 7.0),
                legacy_group_id="g_legacy_mount",
                legacy_auto_rule={"axis": "x", "count": 2},
                semantic_group_id="g_mount",
            ),
        ]
        expected_mountpoints = [mp.to_dict() for mp in composite.mountpoints]

        loaded = Asset.from_dict(
            self._json_round_trip(composite.to_dict())
        )
        saved = self._json_round_trip(loaded.to_dict())
        restored = Asset.from_dict(saved)

        native_restored = restored.get_component("c_native")
        self.assertIsNone(native_restored.attach_anchor)
        self.assertEqual(native_restored.attach_location, native_address)
        self.assertIsNone(native_restored.to_dict()["attach_anchor"])
        self.assertEqual(
            native_restored.to_dict()["attach_location"], native_address,
        )

        legacy_restored = restored.get_component("c_legacy")
        self.assertEqual(legacy_restored.attach_anchor, "bottom")
        self.assertIsNone(legacy_restored.attach_location)
        self.assertNotIn("attach_location", legacy_restored.to_dict())
        self.assertEqual(legacy_restored.parent_anchor, "top")

        self.assertEqual(
            [mp.to_dict() for mp in restored.mountpoints],
            expected_mountpoints,
        )
        self.assertEqual(
            restored.mountpoints[1].semantic_group_id, "g_mount",
        )

    def test_legacy_bottom_and_top_component_round_trip(self):
        for alias in ("bottom", "top"):
            with self.subTest(alias=alias):
                component = Component.from_dict({
                    "id": f"c_{alias}",
                    "asset_id": "asset_legacy_child",
                    "attach_to": "c_parent",
                    "attach_anchor": alias,
                    "parent_anchor": "slot_legacy",
                })
                saved = self._json_round_trip(component.to_dict())
                restored = Component.from_dict(saved)

                self.assertEqual(restored.attach_anchor, alias)
                self.assertIsNone(restored.attach_location)
                self.assertEqual(restored.to_dict()["attach_anchor"], alias)
                self.assertNotIn("attach_location", restored.to_dict())

    def test_all_27_production_native_links_round_trip_without_legacy_alias(self):
        count = 0

        for composite_path in sorted(ASSET_DIR.glob("*.json")):
            source_data = json.loads(
                composite_path.read_text(encoding="utf-8")
            )
            components = source_data.get("components") or {}
            if not any(
                isinstance(record, dict) and record.get("attach_location")
                for record in components.values()
            ):
                continue

            loaded = Asset.from_dict(source_data)
            saved = self._json_round_trip(loaded.to_dict())
            restored = Asset.from_dict(saved)

            for component_id, source_record in components.items():
                address = source_record.get("attach_location")
                if not address:
                    continue
                count += 1
                component = restored.get_component(component_id)
                self.assertIsNone(
                    component.attach_anchor,
                    f"{composite_path.name}:{component_id}",
                )
                self.assertIsNone(
                    component.to_dict()["attach_anchor"],
                    f"{composite_path.name}:{component_id}",
                )
                self.assertEqual(
                    component.attach_location,
                    address,
                    f"{composite_path.name}:{component_id}",
                )

        self.assertEqual(count, 27)


if __name__ == "__main__":
    unittest.main()
