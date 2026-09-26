import unittest

from app.vector_editor.model.mounting.attachment import (
    endpoint_from_component_value,
)


class ComponentEndpointAdapterTests(unittest.TestCase):
    def test_attach_anchor_bottom_is_legacy_alias(self):
        result = endpoint_from_component_value(
            "bottom", field="attach_anchor"
        )

        self.assertEqual(
            result,
            {
                "kind": "legacy_anchor",
                "alias": "bottom",
                "raw_value": "bottom",
            },
        )

    def test_attach_anchor_top_is_legacy_alias(self):
        result = endpoint_from_component_value(
            "top", field="attach_anchor"
        )

        self.assertEqual(
            result,
            {
                "kind": "legacy_anchor",
                "alias": "top",
                "raw_value": "top",
            },
        )

    def test_empty_attach_anchor_has_no_endpoint(self):
        self.assertIsNone(
            endpoint_from_component_value("", field="attach_anchor")
        )

    def test_none_value_has_no_endpoint(self):
        self.assertIsNone(
            endpoint_from_component_value(None, field="parent_anchor")
        )

    def test_parent_mountpoint_tag_extracts_address_and_preserves_raw(self):
        value = "mp_f7e3fca9__2__1"

        result = endpoint_from_component_value(
            value, field="parent_anchor"
        )

        self.assertEqual(
            result,
            {
                "kind": "native_mountpoint",
                "mountpoint_id": "mp_f7e3fca9",
                "index_x": 2,
                "index_y": 1,
                "raw_value": value,
            },
        )

    def test_parent_mountpoint_tag_does_not_validate_index_range(self):
        value = "mp_example__-5__9999"

        result = endpoint_from_component_value(
            value, field="parent_anchor"
        )

        self.assertEqual(result["kind"], "native_mountpoint")
        self.assertEqual(result["index_x"], -5)
        self.assertEqual(result["index_y"], 9999)
        self.assertEqual(result["raw_value"], value)

    def test_parent_slot_is_legacy_slot_and_preserves_full_string(self):
        value = "slot_g_4cb42e0a_0_0"

        result = endpoint_from_component_value(
            value, field="parent_anchor"
        )

        self.assertEqual(
            result,
            {
                "kind": "legacy_slot",
                "raw_value": value,
            },
        )

    def test_parent_top_and_bottom_are_legacy_aliases(self):
        for value in ("top", "bottom"):
            with self.subTest(value=value):
                self.assertEqual(
                    endpoint_from_component_value(
                        value, field="parent_anchor"
                    ),
                    {
                        "kind": "legacy_anchor",
                        "alias": value,
                        "raw_value": value,
                    },
                )

    def test_unknown_parent_alias_is_preserved_without_validation(self):
        value = "unknown_alias"

        result = endpoint_from_component_value(
            value, field="parent_anchor"
        )

        self.assertEqual(result["kind"], "legacy_anchor")
        self.assertEqual(result["alias"], value)
        self.assertEqual(result["raw_value"], value)

    def test_malformed_mountpoint_like_parent_value_is_diagnostic(self):
        value = "mp_f7e3fca9__x__1"

        result = endpoint_from_component_value(
            value, field="parent_anchor"
        )

        self.assertEqual(result, {"kind": None, "raw_value": value})

    def test_empty_parent_anchor_has_no_endpoint(self):
        self.assertIsNone(
            endpoint_from_component_value("", field="parent_anchor")
        )


if __name__ == "__main__":
    unittest.main()
