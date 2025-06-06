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

from . import btrfs_utils
from . import common_fs_utils
from . import rollback_btrfs
from .. import snap_holder

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false


class TestRollbacker(unittest.TestCase):
    def setUp(self):
        common_fs_utils.mount_attributes.cache_clear()
        patcher = mock.patch.object(btrfs_utils, "get_nested_subvs", return_value=[])
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_rollback_btrfs_for_two_snaps(self):
        # config_list = [configs.Config('test.conf', source='/home', dest_prefix='/snaps/@home-')]
        snaps_list = [
            snap_holder.Snapshot("/snaps/@home-20220101130000"),
            snap_holder.Snapshot("/snaps/@root-20220101140000"),
        ]
        snaps_list[0].metadata.source = "/home"
        snaps_list[1].metadata.source = "/root"

        mount_lines = [
            "/dev/BLOCKDEV1 on /root type btrfs (rw,noatime,compress=zstd:3,ssd,discard=async,space_cache=v2,subvolid=123,subvol=/subv_root)",
            "/dev/BLOCKDEV1 on /home type btrfs (rw,noatime,compress=zstd:3,ssd,discard=async,space_cache=v2,subvolid=456,subvol=/subv_home)",
            "/dev/BLOCKDEV1 on /snaps type btrfs (rw,noatime,compress=zstd:3,ssd,discard=async,space_cache=v2,subvolid=789,subvol=/subv_snaps)",
        ]
        with mock.patch.object(
            common_fs_utils, "_mounts", return_value=mount_lines
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

    def test_rollback_btrfs_nested(self):
        snaps_list = [
            snap_holder.Snapshot("/vol/snaps/@home-20220101130000"),
            snap_holder.Snapshot("/vol/snaps/@root-20220101140000"),
        ]
        snaps_list[0].metadata.source = "/vol/nested1"
        snaps_list[1].metadata.source = "/vol/nested2"

        mount_lines = [
            "/dev/BLOCKDEV1 on /vol type btrfs (subvolid=123,subvol=/volume)",
        ]
        with mock.patch.object(
            common_fs_utils, "_mounts", return_value=mount_lines
        ), mock.patch.object(
            rollback_btrfs, "_get_now_str", return_value="20220202220000"
        ):
            generated = rollback_btrfs.rollback_gen(
                source_dests=[(s.metadata.source, s.target) for s in snaps_list]
            )

        expected = """mkdir -p /run/mount/_yabsnap_internal_0
mount /dev/BLOCKDEV1 /run/mount/_yabsnap_internal_0 -o subvolid=5

cd /run/mount/_yabsnap_internal_0

mv nested1 snaps/rollback_20220202220000_nested1
btrfs subvolume snapshot /vol/snaps/@home-20220101130000 nested1

mv nested2 snaps/rollback_20220202220000_nested2
btrfs subvolume snapshot /vol/snaps/@root-20220101140000 nested2

echo Please reboot to complete the rollback.
echo
echo After reboot you may delete -
echo "# sudo btrfs subvolume delete /vol/snaps/rollback_20220202220000_nested1"
echo "# sudo btrfs subvolume delete /vol/snaps/rollback_20220202220000_nested2"
"""
        self.assertEqual(generated, expected.splitlines())


if __name__ == "__main__":
    unittest.main()
