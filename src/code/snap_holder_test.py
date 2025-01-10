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

import datetime
import json
import os
import tempfile
import unittest
from unittest import mock

from . import snap_holder
from .mechanisms import btrfs_mechanism
from .mechanisms import snap_mechanisms

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false

# UTC time.
_NOW = datetime.datetime(2025, 1, 30, hour=12, minute=0, second=0)


class SnapHolderTest(unittest.TestCase):
    def test_create_and_delete(self):
        with tempfile.TemporaryDirectory() as dir:
            snap_destination = os.path.join(dir, "root-20231122193630")
            snap = snap_holder.Snapshot(snap_destination)
            self.assertEqual(snap._snap_type, snap_mechanisms.SnapType.UNKNOWN)

            with mock.patch.object(
                btrfs_mechanism.BtrfsSnapMechanism,
                "verify_volume",
                return_value=True,
            ) as mock_verify_volume, mock.patch.object(
                btrfs_mechanism.BtrfsSnapMechanism, "create", return_value=None
            ) as mock_create:
                snap.create_from(snap_mechanisms.SnapType.BTRFS, "parent")
            mock_verify_volume.assert_called_once_with("parent")
            mock_create.assert_called_once_with("parent", snap_destination)

            snap2 = snap_holder.Snapshot(snap_destination)
            self.assertEqual(snap2._snap_type, snap_mechanisms.SnapType.BTRFS)

            with open(f"{snap_destination}-meta.json") as f:
                self.assertEqual(
                    json.load(f), {"snap_type": "BTRFS", "source": "parent"}
                )

            with mock.patch.object(
                btrfs_mechanism.BtrfsSnapMechanism, "delete", return_value=None
            ) as mock_delete:
                snap2.delete()
            mock_delete.assert_called_once_with(snap_destination)
            self.assertFalse(os.path.exists(f"{snap_destination}-meta.json"))

    def test_backcompat(self):
        with tempfile.TemporaryDirectory() as dir:
            snap_destination = os.path.join(dir, "root-20231122193630")
            with open(f"{snap_destination}-meta.json", "w") as f:
                json.dump({"source": "parent"}, f)
            snap = snap_holder.Snapshot(snap_destination)

            # Without any snap_type, defaults to BTRFS to continue working with old snaps.
            self.assertEqual(snap._snap_type, snap_mechanisms.SnapType.BTRFS)

    def test_filecontent(self):
        with tempfile.TemporaryDirectory() as dir:
            snap_destination = os.path.join(dir, "root-20231122193630")
            snap = snap_holder.Snapshot(snap_destination)
            self.assertEqual(snap.metadata._to_file_content(), {"snap_type": "UNKNOWN"})

            snap.set_ttl("1 hour", now=_NOW)
            self.assertEqual(
                snap.metadata._to_file_content(),
                {"snap_type": "UNKNOWN", "expiry": 1738222200.0},
            )

            # Setting to empty string erases ttl.
            snap.set_ttl("", now=_NOW)
            self.assertEqual(snap.metadata._to_file_content(), {"snap_type": "UNKNOWN"})

    def test_expired(self):
        with tempfile.TemporaryDirectory() as dir:
            snap_destination = os.path.join(dir, "root-20231122193630")
            snap = snap_holder.Snapshot(snap_destination)

            self.assertFalse(snap.metadata.is_expired(_NOW))

            snap.set_ttl("1 h", now=_NOW)
            self.assertFalse(snap.metadata.is_expired(_NOW))

            snap.metadata.expiry = _NOW.timestamp() - 100
            self.assertTrue(snap.metadata.is_expired(_NOW))

            snap.metadata.expiry = _NOW.timestamp() + 100
            self.assertFalse(snap.metadata.is_expired(_NOW))


if __name__ == "__main__":
    unittest.main()
