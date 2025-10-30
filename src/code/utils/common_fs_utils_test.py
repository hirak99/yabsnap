import unittest
from unittest import mock

from . import common_fs_utils

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false


class TestCommonFsUtils(unittest.TestCase):
    def test_get_mount_attributes(self):
        # Fake /etc/mtab lines used for this test.
        mount_lines = [
            "systemd-1 on /home type autofs (rw,relatime,fd=77,pgrp=1,timeout=0,minproto=5,maxproto=5,direct,pipe_ino=2684)",
            "/dev/mapper/luksdev on /home type btrfs (rw,noatime,compress=zstd:3,ssd,discard=async,space_cache=v2,subvolid=2505,subvol=/@home)",
            # A specific volume mapped under /home.
            "/dev/mapper/myhome on /home/myhome type btrfs (rw,noatime,compress=zstd:3,ssd,discard=async,space_cache=v2,subvolid=2506,subvol=/@special_home)",
            # Nested subvolume @nestedvol.
            "/dev/mapper/opened_rootbtrfs on /mnt/rootbtrfs type btrfs (rw,noatime,ssd,discard=async,space_cache=v2,subvolid=5,subvol=/)",
        ]
        with mock.patch.object(common_fs_utils, "_mounts", return_value=mount_lines):
            # Assertiions.
            self.assertEqual(
                common_fs_utils.mount_attributes("/home"),
                common_fs_utils._MountAttributes("/dev/mapper/luksdev", "/@home", 2505),
            )
            self.assertEqual(
                common_fs_utils.mount_attributes("/home/myhome"),
                common_fs_utils._MountAttributes(
                    "/dev/mapper/myhome", "/@special_home", 2506
                ),
            )
            self.assertEqual(
                common_fs_utils.mount_attributes("/mnt/rootbtrfs/@nestedvol"),
                common_fs_utils._MountAttributes(
                    "/dev/mapper/opened_rootbtrfs", "/@nestedvol", 5
                ),
            )
