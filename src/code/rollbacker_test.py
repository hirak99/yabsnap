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
from . import snap_holder

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false


class TestRollbacker(unittest.TestCase):

  def test_checks(self):
    # config_list = [configs.Config('test.conf', source='/home', dest_prefix='/snaps/@home-')]
    snaps_list = [snap_holder.Snapshot('/snaps/@home-20220101130000')]
    snaps_list[0].metadata.source = '/snaps'

    mount_lookup = {'/snaps': '/dev/BLOCKDEV1'}

    def get_mock_mount(mount_pt: str):
      return rollbacker._MountAttributes(device=mount_lookup[mount_pt],
                                         subvol_name='testsubvol')

    with mock.patch.object(rollbacker,
                           '_get_mount_attributes',
                           side_effect=get_mock_mount):
      with mock.patch.object(rollbacker,
                             '_get_now_str',
                             return_value='20220202140000'):
        generated = rollbacker._rollback_snapshots(to_rollback=snaps_list)

    expected = '''#!/bin/bash
# Save this to a script, review and run as root to perform the rollback.

set -uexo pipefail

mkdir -p /run/mount/_yabsnap_internal_0
mount /dev/BLOCKDEV1 /run/mount/_yabsnap_internal_0 -o subvolid=5

cd /run/mount/_yabsnap_internal_0

mv estsubvol estsubvol/rollback_20220202140000_estsubvol
btrfs subvolume snapshot /snaps/@home-20220101130000 estsubvol

echo Please reboot to complete the rollback.
echo
echo After reboot you may delete -
echo "# sudo btrfs subvolume delete /snaps/rollback_20220202140000_estsubvol"
'''
    self.assertEqual(generated, expected.splitlines())


if __name__ == '__main__':
  unittest.main()
