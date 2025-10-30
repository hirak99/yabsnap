import os
import tempfile
import unittest

from . import snap_metadata
from ..mechanisms import snap_mechanisms

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false


# Helper method to load arbitrary json string into SnapMetadata.
def _load_json(json_str: str) -> snap_metadata.SnapMetadata:
    with tempfile.TemporaryDirectory() as dir:
        with open(os.path.join(dir, "meta.json"), "w") as f:
            f.write(json_str)
        return snap_metadata.SnapMetadata.load_file(os.path.join(dir, "meta.json"))


class SnapMetadataTest(unittest.TestCase):
    def test_reconstruction(self):
        metadata = _load_json(
            '{"snap_type": "BTRFS", "source": "parent", "trigger": "S"}'
        )
        expected = snap_metadata.SnapMetadata("BTRFS", "parent", "S")
        self.assertEqual(metadata, expected)

    def test_backcompat(self):
        # Test that unspecified type is read as BTRFS for back compatibility.
        metadata = _load_json('{"source": "parent"}')
        self.assertEqual(metadata.snap_type, snap_mechanisms.SnapType.BTRFS)


if __name__ == "__main__":
    unittest.main()
