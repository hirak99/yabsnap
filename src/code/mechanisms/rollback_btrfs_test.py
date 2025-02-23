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

from . import rollback_btrfs
from .. import snap_holder

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false


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
        with mock.patch.object(rollback_btrfs, "_mtab_contents", return_value=lines):
            # Assertiions.
            self.assertEqual(
                rollback_btrfs._get_mount_attributes_from_mtab("/home"),
                rollback_btrfs._MountAttributes("/dev/mapper/luksdev", "/@home"),
            )
            self.assertEqual(
                rollback_btrfs._get_mount_attributes_from_mtab("/home/myhome"),
                rollback_btrfs._MountAttributes("/dev/mapper/myhome", "/@special_home"),
            )
            self.assertEqual(
                rollback_btrfs._get_mount_attributes_from_mtab(
                    "/mnt/rootbtrfs/@nestedvol"
                ),
                rollback_btrfs._MountAttributes(
                    "/dev/mapper/opened_rootbtrfs", "/@nestedvol"
                ),
            )

    def test_rollback_btrfs_for_two_snaps(self):
        # config_list = [configs.Config('test.conf', source='/home', dest_prefix='/snaps/@home-')]
        snaps_list = [
            snap_holder.Snapshot("/snaps/@home-20220101130000"),
            snap_holder.Snapshot("/snaps/@root-20220101140000"),
        ]
        snaps_list[0].metadata.source = "/home"
        snaps_list[1].metadata.source = "/root"

        mtab_lines = [
            "/dev/BLOCKDEV1 /root btrfs rw,noatime,compress=zstd:3,ssd,discard=async,space_cache=v2,subvolid=123,subvol=/subv_root 0 0",
            "/dev/BLOCKDEV1 /home btrfs rw,noatime,compress=zstd:3,ssd,discard=async,space_cache=v2,subvolid=456,subvol=/subv_home 0 0",
            "/dev/BLOCKDEV1 /snaps btrfs rw,noatime,compress=zstd:3,ssd,discard=async,space_cache=v2,subvolid=789,subvol=/subv_snaps 0 0",
        ]
        with mock.patch.object(
            rollback_btrfs, "_mtab_contents", return_value=mtab_lines
        ), mock.patch.object(
            rollback_btrfs, "_get_now_str", return_value="20220202220000"
        ):
            generated = rollback_btrfs.rollback_gen(
                source_dests=[(s.metadata.source, s.target) for s in snaps_list]
            )

        expected = """mkdir -p /run/mount/_yabsnap_internal_0
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
