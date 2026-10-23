import unittest
from unittest import mock

from ..utils import mtab_parser
from . import btrfs_mechanism

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false


class TestBtrfsWarnIfDestInsideSource(unittest.TestCase):
    def setUp(self):
        mtab_parser.mount_attributes.cache_clear()
        mtab_parser._mount_entries.cache_clear()

    def tearDown(self) -> None:
        mtab_parser.mount_attributes.cache_clear()
        mtab_parser._mount_entries.cache_clear()

    def _mechanism(self):
        return btrfs_mechanism.BtrfsSnapMechanism()

    def test_nested_dest_warns(self):
        # Issue #90: snapshots stored inside the live subvolume.
        findmnt_json = {
            "filesystems": [
                {
                    "target": "/",
                    "source": "/dev/BLOCKDEV1",
                    "fstype": "btrfs",
                    "options": "rw,subvolid=257,subvol=/@",
                },
            ]
        }
        with (
            mock.patch.object(mtab_parser, "_findmnt", return_value=findmnt_json),
            self.assertLogs(level="WARNING") as logs,
        ):
            self._mechanism().warn_if_dest_inside_source("/", "/.snapshots/@-")
        self.assertTrue(any("inside" in line for line in logs.output))
        self.assertTrue(any("Nonstandard layout" in line for line in logs.output))

    def test_separate_snapshots_subvol_quiet(self):
        # Recommended layout: /.snapshots is its own subvolume.
        findmnt_json = {
            "filesystems": [
                {
                    "target": "/",
                    "source": "/dev/BLOCKDEV1",
                    "fstype": "btrfs",
                    "options": "rw,subvolid=257,subvol=/@",
                },
                {
                    "target": "/.snapshots",
                    "source": "/dev/BLOCKDEV1",
                    "fstype": "btrfs",
                    "options": "rw,subvolid=258,subvol=/snapshots",
                },
            ]
        }
        with (
            mock.patch.object(mtab_parser, "_findmnt", return_value=findmnt_json),
            self.assertNoLogs(level="WARNING"),
        ):
            self._mechanism().warn_if_dest_inside_source("/", "/.snapshots/@root-")

    def test_different_device_quiet(self):
        findmnt_json = {
            "filesystems": [
                {
                    "target": "/",
                    "source": "/dev/BLOCKDEV1",
                    "fstype": "btrfs",
                    "options": "rw,subvolid=257,subvol=/@",
                },
                {
                    "target": "/backup",
                    "source": "/dev/BLOCKDEV2",
                    "fstype": "btrfs",
                    "options": "rw,subvolid=257,subvol=/backupsub",
                },
            ]
        }
        with (
            mock.patch.object(mtab_parser, "_findmnt", return_value=findmnt_json),
            self.assertNoLogs(level="WARNING"),
        ):
            self._mechanism().warn_if_dest_inside_source("/", "/backup/@root-")

    def test_unresolvable_layout_never_raises(self):
        with (
            mock.patch.object(
                mtab_parser, "_findmnt", return_value={"filesystems": []}
            ),
            self.assertNoLogs(level="WARNING"),
        ):
            self._mechanism().warn_if_dest_inside_source(
                "/nonexistent", "/also-missing/@-"
            )


if __name__ == "__main__":
    unittest.main()
