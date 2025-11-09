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
        # Fake `findmnt --mtab -J`.
        findmnt_json = {
            "filesystems": [
                # See https://github.com/hirak99/yabsnap/issues/77.
                {
                    "target": "/home/rafael/VirtualBox VMs",
                    "source": "/dev/mapper/root",
                    "fstype": "btrfs",
                    "options": "rw,noatime,lazytime,compress=zstd:1,ssd,discard=async,space_cache=v2,subvolid=613,subvol=/home-rafael/VirtualBox VMs",
                },
                {
                    "target": "/home",
                    "source": "systemd-1",
                    "fstype": "autofs",
                    "options": "rw,relatime,fd=77,pgrp=1,timeout=0,minproto=5,maxproto=5,direct,pipe_ino=2684",
                },
                {
                    "target": "/home",
                    "source": "/dev/mapper/luksdev",
                    "fstype": "btrfs",
                    "options": "rw,noatime,compress=zstd:3,ssd,discard=async,space_cache=v2,subvolid=2505,subvol=/@home",
                },
                # A specific volume mapped under /home.
                {
                    "target": "/home/myhome",
                    "source": "/dev/mapper/myhome",
                    "fstype": "btrfs",
                    "options": "rw,noatime,compress=zstd:3,ssd,discard=async,space_cache=v2,subvolid=2506,subvol=/@special_home",
                },
                # Nested subvolume @nestedvol.
                {
                    "target": "/mnt/rootbtrfs",
                    "source": "/dev/mapper/opened_rootbtrfs",
                    "fstype": "btrfs",
                    "options": "rw,noatime,ssd,discard=async,space_cache=v2,subvolid=5,subvol=/",
                },
                # Assume "/@/testnested" is mounted at "/testnested".
                {
                    "target": "/",
                    "source": "/dev/vda2",
                    "fstype": "btrfs",
                    "options": "rw,relatime,discard=async,space_cache=v2,subvolid=258,subvol=/@",
                },
            ]
        }

        with mock.patch.object(mtab_parser, "_findmnt", return_value=findmnt_json):
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
