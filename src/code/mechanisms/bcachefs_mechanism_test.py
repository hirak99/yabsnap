import unittest
from unittest import mock

from ..utils import mtab_parser
from . import bcachefs_mechanism

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false


class TestBcachefsWarnIfDestInsideSource(unittest.TestCase):
    def setUp(self):
        mtab_parser._mount_entries.cache_clear()

    def tearDown(self) -> None:
        mtab_parser._mount_entries.cache_clear()

    def _mechanism(self):
        return bcachefs_mechanism.BcachefsSnapMechanism()

    def test_same_mount_nested_warns(self):
        findmnt_json = {
            "filesystems": [
                {
                    "target": "/",
                    "source": "/dev/BLOCKDEV1",
                    "fstype": "bcachefs",
                    "options": "rw",
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

    def test_separately_mounted_quiet(self):
        findmnt_json = {
            "filesystems": [
                {
                    "target": "/",
                    "source": "/dev/BLOCKDEV1",
                    "fstype": "bcachefs",
                    "options": "rw",
                },
                {
                    "target": "/.snapshots",
                    "source": "/dev/BLOCKDEV1",
                    "fstype": "bcachefs",
                    "options": "rw",
                },
            ]
        }
        with (
            mock.patch.object(mtab_parser, "_findmnt", return_value=findmnt_json),
            self.assertNoLogs(level="WARNING"),
        ):
            self._mechanism().warn_if_dest_inside_source("/", "/.snapshots/@-")

    def test_different_device_quiet(self):
        findmnt_json = {
            "filesystems": [
                {
                    "target": "/",
                    "source": "/dev/BLOCKDEV1",
                    "fstype": "bcachefs",
                    "options": "rw",
                },
            ]
        }
        with (
            mock.patch.object(mtab_parser, "_findmnt", return_value=findmnt_json),
            self.assertNoLogs(level="WARNING"),
        ):
            self._mechanism().warn_if_dest_inside_source("/home", "/backup/@home-")

    def test_dest_outside_source_quiet(self):
        # Path check fails first; mtab is never consulted.
        with self.assertNoLogs(level="WARNING"):
            self._mechanism().warn_if_dest_inside_source("/home", "/backup/@home-")


if __name__ == "__main__":
    unittest.main()
