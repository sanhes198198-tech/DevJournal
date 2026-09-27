import json
import unittest

from app.vector_editor.model import Asset, Component
from app.vector_editor.model.mounting import Attachment


class UnifiedAttachmentModelTests(unittest.TestCase):
    def test_attachment_represents_parent_and_both_native_locations(self):
        parent_location = {
            "mountpoint_id": "mp_parent",
            "index_x": 2,
            "index_y": 1,
        }
        child_location = {
            "mountpoint_id": "mp_child",
            "index_x": 0,
            "index_y": 3,
        }
        attachment = Attachment(
            parent_component_id="c_parent",
            parent_location=parent_location,
            child_location=child_location,
        )

        self.assertTrue(attachment.is_relationship())
        self.assertTrue(attachment.is_valid())
        self.assertEqual(attachment.parent_component_id, "c_parent")
        self.assertEqual(attachment.parent_location, parent_location)
        self.assertEqual(attachment.child_location, child_location)

        restored = Attachment.from_dict(attachment.to_dict())
        self.assertTrue(restored.is_relationship())
        self.assertEqual(restored.to_dict(), attachment.to_dict())

    def test_component_compatibility_properties_proxy_to_one_attachment(self):
        component = Component(
            id="c_child",
            asset_id="asset_child",
            attach_to="c_parent",
            attach_location={
                "mountpoint_id": "mp_child",
                "index_x": 1,
                "index_y": 0,
            },
            parent_location={
                "mountpoint_id": "mp_parent",
                "index_x": 0,
                "index_y": 2,
            },
        )
        relationship = component.attachment

        component.attach_to = "c_new_parent"
        component.attach_location = {
            "mountpoint_id": "mp_child_new",
            "index_x": 0,
            "index_y": 0,
        }
        component.parent_location = {
            "mountpoint_id": "mp_parent_new",
            "index_x": 2,
            "index_y": 0,
        }

        self.assertIs(component.attachment, relationship)
        self.assertEqual(
            relationship.parent_component_id, "c_new_parent",
        )
        self.assertEqual(
            relationship.child_location, component.attach_location,
        )
        self.assertEqual(
            relationship.parent_location, component.parent_location,
        )

    def test_legacy_aliases_remain_compatibility_fields(self):
        component = Component(
            id="c_legacy",
            asset_id="asset_child",
            attach_to="c_parent",
            attach_anchor="bottom",
            parent_anchor="top",
        )

        self.assertTrue(component.attachment.is_relationship())
        self.assertFalse(component.attachment.is_valid())
        self.assertEqual(component.attachment.parent_component_id, "c_parent")
        self.assertIsNone(component.attachment.child_location)
        self.assertIsNone(component.attachment.parent_location)
        self.assertEqual(component.attach_anchor, "bottom")
        self.assertEqual(component.parent_anchor, "top")

        saved = component.to_dict()
        self.assertNotIn("attachment", saved)
        self.assertEqual(saved["attach_anchor"], "bottom")
        self.assertEqual(saved["parent_anchor"], "top")
        self.assertNotIn("attach_location", saved)
        self.assertNotIn("parent_location", saved)

    def test_old_native_parent_tag_adapts_and_preserves_raw_tag(self):
        component = Component.from_dict({
            "id": "c_old_native",
            "asset_id": "asset_child",
            "attach_to": "c_parent",
            "parent_anchor": "mp_parent__2__1",
        })

        expected = {
            "mountpoint_id": "mp_parent",
            "index_x": 2,
            "index_y": 1,
        }
        self.assertEqual(component.attachment.parent_location, expected)
        self.assertEqual(component.parent_anchor, "mp_parent__2__1")

        # The flat compatibility schema keeps the source tag and writes the
        # already-supported explicit native parent address as well.
        saved = component.to_dict()
        self.assertEqual(saved["parent_anchor"], "mp_parent__2__1")
        self.assertEqual(saved["parent_location"], expected)
        self.assertNotIn("attachment", saved)
        self.assertEqual(
            Component.from_dict(json.loads(json.dumps(saved))).attachment
            .parent_location,
            expected,
        )

    def test_asset_round_trip_keeps_flat_component_persistence(self):
        component = Component(
            id="c_native",
            asset_id="asset_child",
            attach_to="c_parent",
            attach_anchor=None,
            parent_anchor="",
            attach_location={
                "mountpoint_id": "mp_child",
                "index_x": 0,
                "index_y": 0,
            },
            parent_location={
                "mountpoint_id": "mp_parent",
                "index_x": 1,
                "index_y": 2,
            },
        )
        asset = Asset(asset_id="asset_composite", components={component.id: component})

        payload = json.loads(json.dumps(asset.to_dict()))
        component_payload = payload["components"][component.id]
        restored = Asset.from_dict(payload).get_component(component.id)

        self.assertNotIn("attachment", component_payload)
        self.assertEqual(
            component_payload["attach_location"], component.attach_location,
        )
        self.assertEqual(
            component_payload["parent_location"], component.parent_location,
        )
        self.assertEqual(
            restored.attachment.to_dict(), component.attachment.to_dict(),
        )

    def test_clear_attachment_clears_the_unified_relation(self):
        component = Component(
            id="c_child",
            asset_id="asset_child",
            attach_to="c_parent",
            attach_anchor="bottom",
            parent_anchor="top",
            attach_location={
                "mountpoint_id": "mp_child",
                "index_x": 0,
                "index_y": 0,
            },
            parent_location={
                "mountpoint_id": "mp_parent",
                "index_x": 0,
                "index_y": 0,
            },
        )
        attachment = component.attachment

        component.clear_attachment()

        self.assertIs(component.attachment, attachment)
        self.assertEqual(attachment.parent_component_id, "")
        self.assertIsNone(attachment.child_location)
        self.assertIsNone(attachment.parent_location)
        self.assertEqual(component.attach_anchor, "")
        self.assertEqual(component.parent_anchor, "")


if __name__ == "__main__":
    unittest.main()
