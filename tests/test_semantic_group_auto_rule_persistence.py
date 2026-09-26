import copy
import json
from pathlib import Path
import unittest

from app.vector_editor.model import Asset, SemanticGroup


_ASSET_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "vector_editor"
    / "assets"
    / "d5d9aadc6a4c.json"
)


class SemanticGroupAutoRulePersistenceTests(unittest.TestCase):
    @staticmethod
    def _real_payload():
        return json.loads(_ASSET_PATH.read_text(encoding="utf-8"))

    def test_a_auto_rule_loads_from_json(self):
        rule = {"axis": "y", "step": -3.0, "skip_groups": []}
        group = SemanticGroup.from_dict({
            "id": "g_rule",
            "name": "window_slot",
            "label": "Slot",
            "node_ids": ["n_1"],
            "auto_rule": rule,
        })

        self.assertEqual(group.auto_rule, rule)

    def test_b_auto_rule_round_trips_without_content_changes(self):
        rule = {
            "axis": "y",
            "step": -3.0,
            "until_group": "window_slot",
            "skip_groups": [],
            "axis_x": "x",
        }
        payload = {
            "id": "g_rule",
            "name": "window_slot",
            "label": "Slot",
            "node_ids": ["n_1"],
            "auto_rule": rule,
        }

        self.assertEqual(SemanticGroup.from_dict(payload).to_dict(), payload)

    def test_c_explicit_null_auto_rule_remains_null(self):
        payload = {
            "id": "g_null",
            "name": "anchor_bottom",
            "label": "Bottom",
            "node_ids": ["n_1"],
            "auto_rule": None,
        }

        restored = SemanticGroup.from_dict(payload)
        self.assertIsNone(restored.auto_rule)
        self.assertIn("auto_rule", restored.to_dict())
        self.assertIsNone(restored.to_dict()["auto_rule"])

    def test_d_absent_auto_rule_remains_absent(self):
        payload = {
            "id": "g_no_rule",
            "name": "anchor_bottom",
            "label": "Bottom",
            "node_ids": ["n_1"],
        }

        restored = SemanticGroup.from_dict(payload)
        self.assertIsNone(restored.auto_rule)
        self.assertNotIn("auto_rule", restored.to_dict())
        self.assertNotIn("auto_rule", SemanticGroup().to_dict())

    def test_e_all_real_non_null_rules_survive_asset_load_save(self):
        payload = self._real_payload()
        original_rules = {
            group_id: copy.deepcopy(group["auto_rule"])
            for group_id, group in payload["semantic_groups"].items()
            if group.get("auto_rule") is not None
        }

        saved = Asset.from_dict(payload).to_dict()
        saved_rules = {
            group_id: group["auto_rule"]
            for group_id, group in saved["semantic_groups"].items()
            if group.get("auto_rule") is not None
        }

        self.assertEqual(len(original_rules), 4)
        self.assertEqual(saved_rules, original_rules)

    def test_f_migration_receives_rules_loaded_from_real_asset(self):
        payload = self._real_payload()
        original_rules = {
            group_id: group["auto_rule"]
            for group_id, group in payload["semantic_groups"].items()
            if group.get("auto_rule") is not None
        }

        asset = Asset.from_dict(payload)
        migrated_rules = {
            point.legacy_group_id: point.legacy_auto_rule
            for point in asset.mountpoints
        }

        self.assertEqual(migrated_rules, original_rules)

    def test_g_groups_without_auto_rule_keep_existing_payload(self):
        group = SemanticGroup(
            id="g_plain",
            name="foundation",
            label="Foundation",
            node_ids=["n_1", "n_2"],
        )

        self.assertEqual(group.to_dict(), {
            "id": "g_plain",
            "name": "foundation",
            "label": "Foundation",
            "node_ids": ["n_1", "n_2"],
        })

    def test_h_asset_round_trip_keeps_unrelated_real_fields(self):
        payload = self._real_payload()
        saved = Asset.from_dict(payload).to_dict()

        for key, value in payload.items():
            if key in {"semantic_groups", "mountpoints"}:
                continue
            self.assertEqual(saved[key], value, key)


if __name__ == "__main__":
    unittest.main()
