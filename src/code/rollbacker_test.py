# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
from unittest import mock

from . import rollbacker
from . import os_utils
from . import snap_holder

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false

_MOUNT_LOOKUP = {
    "/snaps": ("/dev/BLOCKDEV1", "/subv_snaps"),
    "/home": ("/dev/BLOCKDEV1", "/subv_home"),
    "/root": ("/dev/BLOCKDEV1", "/subv_root"),
}


def _mock_get_mount_attributes_from_mtab(mount_pt: str):
    return rollbacker._MountAttributes(
        device=_MOUNT_LOOKUP[mount_pt][0], subvol_name=_MOUNT_LOOKUP[mount_pt][1]
    )


class TestRollbacker(unittest.TestCase):
    def test_get_mount_attributes(self):
        # Fake /etc/mtab lines used for this test.
        lines = [
            "/dev/mapper/luksdev /home btrfs rw,noatime,compress=zstd:3,ssd,discard=async,space_cache=v2,subvolid=2505,subvol=/@home 0 0",
            # A specific volume mapped under /home.
            "/dev/mapper/myhome /home/myhome btrfs rw,noatime,compress=zstd:3,ssd,discard=async,space_cache=v2,subvolid=2505,subvol=/@special_home 0 0",
            # Nested subvolume @nestedvol.
            "/dev/mapper/opened_rootbtrfs /mnt/rootbtrfs btrfs rw,noatime,ssd,discard=async,space_cache=v2,subvolid=5,subvol=/ 0 0",
        ]
        # Assertiions.
        self.assertEqual(
            rollbacker._MountAttributes("/dev/mapper/luksdev", "/@home"),
            rollbacker._get_mount_attributes("/home", lines),
        )
        self.assertEqual(
            rollbacker._MountAttributes("/dev/mapper/myhome", "/@special_home"),
            rollbacker._get_mount_attributes("/home/myhome", lines),
        )
        self.assertEqual(
            rollbacker._MountAttributes("/dev/mapper/opened_rootbtrfs", "/@nestedvol"),
            rollbacker._get_mount_attributes("/mnt/rootbtrfs/@nestedvol", lines),
        )

    def test_rollback_for_two_snaps(self):
        # config_list = [configs.Config('test.conf', source='/home', dest_prefix='/snaps/@home-')]
        snaps_list = [
            snap_holder.Snapshot("/snaps/@home-20220101130000"),
            snap_holder.Snapshot("/snaps/@root-20220101140000"),
        ]
        snaps_list[0].metadata.source = "/home"
        snaps_list[1].metadata.source = "/root"

        with mock.patch.object(
            os_utils, "is_btrfs_volume", return_value=True
        ) as mock_is_btrfs_volume, mock.patch.object(
            rollbacker, "_get_now_str", return_value="20220202220000"
        ), mock.patch.object(
            rollbacker,
            "_get_mount_attributes_from_mtab",
            side_effect=_mock_get_mount_attributes_from_mtab,
        ):
            generated = rollbacker._rollback_snapshots(snapshots=snaps_list)

        self.assertEqual(
            mock_is_btrfs_volume.call_args_list,
            [mock.call("/home"), mock.call("/root")],
        )

        expected = """#!/bin/bash
# Save this to a script, review and run as root to perform the rollback.

set -uexo pipefail

mkdir -p /run/mount/_yabsnap_internal_0
mount /dev/BLOCKDEV1 /run/mount/_yabsnap_internal_0 -o subvolid=5

cd /run/mount/_yabsnap_internal_0

mv subv_home subv_snaps/rollback_20220202220000_subv_home
btrfs subvolume snapshot /snaps/@home-20220101130000 subv_home

mv subv_root subv_snaps/rollback_20220202220000_subv_root
btrfs subvolume snapshot /snaps/@root-20220101140000 subv_root

echo Please reboot to complete the rollback.
echo
echo After reboot you may delete -
echo "# sudo btrfs subvolume delete /snaps/rollback_20220202220000_subv_home"
echo "# sudo btrfs subvolume delete /snaps/rollback_20220202220000_subv_root"
"""
        self.assertEqual(generated, expected.splitlines())


if __name__ == "__main__":
    unittest.main()
