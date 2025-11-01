import os
import tempfile
import unittest

from . import snap_metadata
from ..mechanisms import snap_type_enum

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false


# Helper method to load arbitrary json string into SnapMetadata.
def _load_json(json_str: str) -> snap_metadata.SnapMetadata:
    with tempfile.TemporaryDirectory() as dir:
        with open(os.path.join(dir, "meta.json"), "w") as f:
            f.write(json_str)
        return snap_metadata.SnapMetadata.load_file(os.path.join(dir, "meta.json"))


class SnapMetadataTest(unittest.TestCase):
    def test_to_file_content(self):
        metadata = snap_metadata.SnapMetadata(
            version="test",
            snap_type=snap_type_enum.SnapType.BTRFS,
            source="parent",
            expiry=1234,
            btrfs=snap_metadata.Btrfs(source_subvol="subvol"),
        )
        self.assertEqual(
            metadata._to_file_content(),
            {
                "version": "test",
                "snap_type": "BTRFS",
                "source": "parent",
                "expiry": 1234,
                "btrfs": {"source_subvol": "subvol"},
            },
        )

    def test_loading(self):
        loaded = _load_json(
            '{"version": "test", "snap_type": "BTRFS", "source": "parent", "trigger": "S", "btrfs": {"source_subvol": "subvol"}}'
        )
        expected = snap_metadata.SnapMetadata(
            version="test",
            snap_type=snap_type_enum.SnapType.BTRFS,
            source="parent",
            trigger="S",
            btrfs=snap_metadata.Btrfs(source_subvol="subvol"),
        )
        self.assertEqual(loaded, expected)

    def test_backcompat(self):
        # Test that unspecified type is read as BTRFS for back compatibility.
        metadata = _load_json('{"source": "parent"}')
        self.assertEqual(metadata.snap_type, snap_type_enum.SnapType.BTRFS)

    def test_default_version(self):
        metadata = snap_metadata.SnapMetadata()
        self.assertNotEqual(metadata.version, "1.0.0")
        self.assertIsInstance(metadata.version, str)

    def test_unknown_version(self):
        # If version is not present, it defaults to "1.0.0".
        metadata = _load_json('{"source": "parent"}')
        self.assertEqual(metadata.version, "1.0.0")


if __name__ == "__main__":
    unittest.main()
