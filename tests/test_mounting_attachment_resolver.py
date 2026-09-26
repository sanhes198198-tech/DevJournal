import unittest

from app.vector_editor.model import Asset, SemanticGroup
from app.vector_editor.model.mounting import Attachment, Distribution, MountPoint


def _asset_with_geometry(points, groups):
    node_ids = list(points)
    contour = [points[node_id] for node_id in node_ids]
    geometry = {
        "contour": contour,
        "closed": False,
        "units": "m",
        "node_ids": node_ids,
        "groups": {},
        "extra_edges": [],
        "arcs": [],
        "extra_points": [],
        "extra_node_ids": [],
    }
    asset_groups = {
        group_id: SemanticGroup(
            id=group_id,
            name=name,
            node_ids=group_node_ids,
        )
        for group_id, name, group_node_ids in groups
    }
    return Asset(geometry=geometry, semantic_groups=asset_groups)


class AttachmentResolverTests(unittest.TestCase):
    def test_resolves_native_mountpoint_location(self):
        asset = Asset()
        asset.mountpoints = [MountPoint(id="mp_native", position=(2.5, -1.25))]

        position, source = Attachment(
            target_type="mountpoint",
            target_id="mp_native",
            location={"x": 0, "y": 0},
        ).resolve(asset)

        self.assertEqual(position, (2.5, -1.25))
        self.assertEqual(source, "native_mountpoint")

    def test_resolves_relative_mountpoint_with_bbox(self):
        asset = Asset()
        asset.mountpoints = [
            MountPoint(
                id="mp_grid",
                position=(99.0, 99.0),
                distribution=Distribution(count_x=3, count_y=2),
                anchor_mode="relative_xy",
                anchor_x=0.5,
                anchor_y=0.5,
            )
        ]

        position, source = Attachment(
            target_type="mountpoint",
            target_id="mp_grid",
            location={"x": 2, "y": 1},
        ).resolve(asset, bbox=(0.0, 0.0, 10.0, 8.0))

        self.assertEqual(position, (10.0, 8.0))
        self.assertEqual(source, "native_mountpoint")

    def test_relative_mountpoint_requires_bbox(self):
        asset = Asset()
        asset.mountpoints = [
            MountPoint(id="mp_relative", anchor_mode="relative_xy")
        ]

        with self.assertRaisesRegex(ValueError, "bbox is required"):
            Attachment(
                target_type="mountpoint",
                target_id="mp_relative",
                location={"x": 0, "y": 0},
            ).resolve(asset)

    def test_unknown_mountpoint_raises_value_error(self):
        with self.assertRaisesRegex(ValueError, "Unknown MountPoint"):
            Attachment(
                target_type="mountpoint",
                target_id="mp_missing",
                location={"x": 0, "y": 0},
            ).resolve(Asset())

    def test_invalid_mountpoint_index_raises_value_error(self):
        asset = Asset()
        asset.mountpoints = [
            MountPoint(
                id="mp_single",
                position=(1.0, 2.0),
                distribution=Distribution(count_x=2),
            )
        ]

        with self.assertRaisesRegex(
            ValueError, "Invalid MountPoint location index"
        ):
            Attachment(
                target_type="mountpoint",
                target_id="mp_single",
                location={"x": 2, "y": 0},
            ).resolve(asset)

    def test_resolves_legacy_bottom_and_top(self):
        asset = _asset_with_geometry(
            {
                "n0": (0.0, 0.0),
                "n1": (0.0, 2.0),
                "n2": (2.0, 2.0),
                "n3": (2.0, 4.0),
            },
            [
                ("g_bottom", "anchor_bottom", ["n0", "n1"]),
                ("g_top", "anchor_top", ["n2", "n3"]),
            ],
        )

        for alias, expected in (
            ("bottom", (0.0, 1.0)),
            ("top", (2.0, 3.0)),
        ):
            with self.subTest(alias=alias):
                position, source = Attachment(
                    target_type="anchor",
                    target_id=alias,
                ).resolve(asset)

                self.assertEqual(position, expected)
                self.assertEqual(source, "legacy_anchor")

    def test_unknown_legacy_alias_raises_value_error(self):
        asset = _asset_with_geometry(
            {"n0": (0.0, 0.0)},
            [("g_bottom", "anchor_bottom", ["n0"])],
        )

        with self.assertRaisesRegex(ValueError, "Unknown legacy anchor alias"):
            Attachment(
                target_type="anchor", target_id="center"
            ).resolve(asset)

    def test_ambiguous_alias_uses_asset_anchors_priority(self):
        asset = _asset_with_geometry(
            {
                "n0": (0.0, 0.0),
                "n1": (2.0, 0.0),
                "n2": (10.0, 10.0),
                "n3": (14.0, 10.0),
            },
            [
                # The ordinary alias is inserted first, but explicit anchor_*
                # groups have priority in Asset.anchors().
                ("g_top", "top", ["n0", "n1"]),
                ("g_anchor_top", "anchor_top", ["n2", "n3"]),
            ],
        )

        position, source = Attachment(
            target_type="anchor",
            target_id="top",
        ).resolve(asset)

        self.assertEqual(position, (12.0, 10.0))
        self.assertEqual(source, "legacy_anchor")
