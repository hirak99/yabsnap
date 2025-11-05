import unittest
from unittest import mock

from . import mtab_parser

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false

# '/dev/vda2 on / type btrfs (rw,relatime,discard=async,space_cache=v2,subvolid=258,subvol=/@)'
# subvol_name="/@"
# mount_point="/testnested"
# tokens.mtab_mount_pt="/"
# REVISED subvol_name="/@/testnested"


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
            # Assume "/@/testnested" is mounted at "/testnested".
            "/dev/vda2 on / type btrfs (rw,relatime,discard=async,space_cache=v2,subvolid=258,subvol=/@)",
        ]
        with mock.patch.object(mtab_parser, "_mounts", return_value=mount_lines):
            # Assertiions.
            self.assertEqual(
                mtab_parser.mount_attributes("/home"),
                mtab_parser._MountAttributes("/dev/mapper/luksdev", "/@home", 2505),
            )
            self.assertEqual(
                mtab_parser.mount_attributes("/home/myhome"),
                mtab_parser._MountAttributes(
                    "/dev/mapper/myhome", "/@special_home", 2506
                ),
            )
            self.assertEqual(
                mtab_parser.mount_attributes("/mnt/rootbtrfs/@nestedvol"),
                mtab_parser._MountAttributes(
                    "/dev/mapper/opened_rootbtrfs", "/@nestedvol", 5
                ),
            )
            self.assertEqual(
                mtab_parser.mount_attributes("/testnested"),
                mtab_parser._MountAttributes("/dev/vda2", "/@/testnested", 258),
            )
