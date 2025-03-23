import unittest
from unittest import mock

from . import common_fs_utils

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false


class TestCommonFsUtils(unittest.TestCase):
    def test_get_mount_attributes(self):
        # Fake /etc/mtab lines used for this test.
        mtab_lines = [
            "/dev/mapper/luksdev /home btrfs rw,noatime,compress=zstd:3,ssd,discard=async,space_cache=v2,subvolid=2505,subvol=/@home 0 0",
            # A specific volume mapped under /home.
            "/dev/mapper/myhome /home/myhome btrfs rw,noatime,compress=zstd:3,ssd,discard=async,space_cache=v2,subvolid=2505,subvol=/@special_home 0 0",
            # Nested subvolume @nestedvol.
            "/dev/mapper/opened_rootbtrfs /mnt/rootbtrfs btrfs rw,noatime,ssd,discard=async,space_cache=v2,subvolid=5,subvol=/ 0 0",
        ]
        with mock.patch.object(
            common_fs_utils, "_mtab_contents", return_value=mtab_lines
        ):
            # Assertiions.
            self.assertEqual(
                common_fs_utils.mount_attributes("/home"),
                common_fs_utils._MountAttributes("/dev/mapper/luksdev", "/@home"),
            )
            self.assertEqual(
                common_fs_utils.mount_attributes("/home/myhome"),
                common_fs_utils._MountAttributes(
                    "/dev/mapper/myhome", "/@special_home"
                ),
            )
            self.assertEqual(
                common_fs_utils.mount_attributes("/mnt/rootbtrfs/@nestedvol"),
                common_fs_utils._MountAttributes(
                    "/dev/mapper/opened_rootbtrfs", "/@nestedvol"
                ),
            )
