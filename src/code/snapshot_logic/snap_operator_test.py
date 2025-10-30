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

import contextlib
import datetime
import time
import unittest
from unittest import mock

from . import auto_cleanup_without_ttl
from . import snap_holder
from . import snap_operator
from .. import configs
from ..mechanisms import btrfs_mechanism
from ..mechanisms import snap_mechanisms

from typing import Iterator

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false

# UTC time.
# Alternative to using pytz.localize(...), and removes dependency on pytz.
_FAKE_NOW = datetime.datetime(2023, 2, 15, hour=12, minute=0, second=0)


def _utc_to_local(yyyymmddhhmmss: str) -> datetime.datetime:
    return (
        (
            datetime.datetime.strptime(yyyymmddhhmmss, "%Y%m%d%H%M%S")
            - datetime.timedelta(seconds=time.timezone)
        )
        .astimezone()
        .replace(tzinfo=None)
    )


def _utc_to_local_str(yyyymmddhhmmss: str) -> str:
    return _utc_to_local(yyyymmddhhmmss).strftime("%Y%m%d%H%M%S")


class SnapOperatorTest(unittest.TestCase):
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self._old_snaps: list[snap_holder.Snapshot] = []

    def test_scheduled_without_preexisting(self):
        snapper = snap_operator.SnapOperator(
            config=configs.Config(
                config_file="config_file",
                source="snap_source",
                dest_prefix="dest_prefix",
            ),
            now=_FAKE_NOW,
        )
        snapper.scheduled()
        self._mock_create_from.assert_called_once_with(
            snap_mechanisms.SnapType.BTRFS, "snap_source"
        )

    def test_scheduled_not_triggered(self):
        self._old_snaps = [
            snap_holder.Snapshot(
                # Added 10 minutes, to counteract DURATION_BUFFER.
                "/tmp/nodir/@home-"
                + _utc_to_local_str("20230213" "001000")
            )
        ]
        self._old_snaps[-1].metadata.trigger = "S"
        trigger_interval = datetime.timedelta(hours=12).total_seconds()
        snapper = snap_operator.SnapOperator(
            config=configs.Config(
                config_file="config_file",
                source="snap_source",
                dest_prefix="dest_prefix",
                trigger_interval=trigger_interval,
            ),
            now=_utc_to_local("20230213" "110000"),
        )
        snapper.scheduled()
        self._mock_delete.assert_not_called()
        self._mock_create_from.assert_not_called()

    def test_scheduled_triggered(self):
        self._old_snaps = [
            snap_holder.Snapshot(
                # Added 10 minutes, to counteract DURATION_BUFFER.
                "/tmp/nodir/@home-"
                + _utc_to_local_str("20230213" "001000")
            )
        ]
        self._old_snaps[-1].metadata.trigger = "S"
        trigger_interval = datetime.timedelta(hours=12).total_seconds()
        snapper = snap_operator.SnapOperator(
            config=configs.Config(
                config_file="config_file",
                source="snap_source",
                dest_prefix="dest_prefix",
                trigger_interval=trigger_interval,
            ),
            now=_utc_to_local("20230213" "130000"),
        )
        snapper.scheduled()
        self._mock_delete.assert_called_once_with()
        self._mock_create_from.assert_called_once_with(
            snap_mechanisms.SnapType.BTRFS, "snap_source"
        )

    def test_scheduled_ttl_expiry(self):
        self._old_snaps = [
            snap_holder.Snapshot(
                # Added 10 minutes, to counteract DURATION_BUFFER.
                "/tmp/nodir/@home-"
                + _utc_to_local_str("20230213" "001000")
            )
        ]
        self._old_snaps[-1].metadata.trigger = "S"
        # Set it as expired.
        self._old_snaps[-1].metadata.expiry = _utc_to_local(
            "20230213" "000100"
        ).timestamp()
        # Set trigger every 12 hours.
        trigger_interval = datetime.timedelta(hours=12).total_seconds()
        snapper = snap_operator.SnapOperator(
            config=configs.Config(
                config_file="config_file",
                source="snap_source",
                dest_prefix="dest_prefix",
                trigger_interval=trigger_interval,
            ),
            # Say the scheduled() happens just 10 seconds later.
            now=_utc_to_local("20230213" "001010"),
        )
        snapper.scheduled()
        # Even if the scheduled() call happens before trigger, snap is deleted().
        self._mock_delete.assert_called_once_with()
        self._mock_create_from.assert_called_once_with(
            snap_mechanisms.SnapType.BTRFS, "snap_source"
        )

    def test_pachook(self):
        def setup_n_snaps(n: int):
            self._old_snaps = [
                snap_holder.Snapshot(f"/tmp/nodir/@home-202311150{k}0000")
                for k in range(n)
            ]
            for snap in self._old_snaps:
                snap.metadata.trigger = "I"
            trigger_interval = datetime.timedelta(hours=12).total_seconds()
            snapper = snap_operator.SnapOperator(
                config=configs.Config(
                    config_file="config_file",
                    source="snap_source",
                    dest_prefix="dest_prefix",
                    trigger_interval=trigger_interval,
                ),
                now=_utc_to_local("20230213" "130000"),
            )
            self._mock_delete.reset_mock()
            self._mock_create_from.reset_mock()
            return snapper

        # Have 0, need 0 => Create 0, delete 0.
        setup_n_snaps(0)._create_and_maintain_n_backups(0, "I", None)
        self._mock_create_from.assert_not_called()
        self._mock_delete.assert_not_called()

        # Have 0, need 3 => Create 1, delete 0.
        setup_n_snaps(0)._create_and_maintain_n_backups(3, "I", None)
        self._mock_create_from.assert_called_once_with(
            snap_mechanisms.SnapType.BTRFS, "snap_source"
        )
        self._mock_delete.assert_not_called()

        # Have 3, need 4 => Create 1, delete 0.
        setup_n_snaps(3)._create_and_maintain_n_backups(4, "I", None)
        self._mock_create_from.assert_called_once_with(
            snap_mechanisms.SnapType.BTRFS, "snap_source"
        )
        self._mock_delete.assert_not_called()

        # Have 3, need 3 => Create 1, delete 1.
        setup_n_snaps(3)._create_and_maintain_n_backups(3, "I", None)
        self._mock_create_from.assert_called_once_with(
            snap_mechanisms.SnapType.BTRFS, "snap_source"
        )
        self._mock_delete.assert_called_once_with()

        # Have 3, need 2 => Create 1, delete 2.
        setup_n_snaps(3)._create_and_maintain_n_backups(2, "I", None)
        self._mock_create_from.assert_called_once_with(
            snap_mechanisms.SnapType.BTRFS, "snap_source"
        )
        self.assertEqual(self._mock_delete.call_count, 2)

        # Have 3, need 0 => Create 0, delete 3.
        setup_n_snaps(3)._create_and_maintain_n_backups(0, "I", None)
        self._mock_create_from.assert_not_called()
        self.assertEqual(self._mock_delete.call_count, 3)

    def test_delete_expired_ttl(self):
        self._old_snaps = [
            snap_holder.Snapshot("/tmp/nodir/@home-20230213001000"),
            snap_holder.Snapshot("/tmp/nodir/@home-20230214001000"),
        ]
        self._old_snaps[-1].metadata.trigger = "S"
        self._old_snaps[-1].metadata.comment = "snap1"

        self._old_snaps[-2].metadata.trigger = "I"
        self._old_snaps[-2].metadata.comment = "snap2"
        # Expired 100 seconds ago.
        self._old_snaps[-2].metadata.expiry = _FAKE_NOW.timestamp() - 100

        snapper = snap_operator.SnapOperator(
            config=configs.Config(
                config_file="config_file",
                source="snap_source",
                dest_prefix="/tmp/nodir/@home-",
            ),
            now=_FAKE_NOW,
        )
        remaining = snapper._delete_expired_ttl(self._old_snaps)

        # The method stores the snap for deletion later.
        self._mock_delete.assert_not_called()
        self.assertEqual(len(snapper._scheduled_to_delete), 1)
        self.assertEqual(snapper._scheduled_to_delete[0].metadata.comment, "snap2")

        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].metadata.comment, "snap1")

    def test_list_json(self):
        self._old_snaps = [snap_holder.Snapshot("/tmp/nodir/@home-20230213001000")]
        self._old_snaps[-1].metadata.trigger = "S"
        self._old_snaps[-1].metadata.comment = "comment"
        snapper = snap_operator.SnapOperator(
            config=configs.Config(
                config_file="config_file",
                source="snap_source",
                dest_prefix="/tmp/nodir/@home-",
            ),
            now=_FAKE_NOW,
        )
        self.assertEqual(
            list(snapper._snaps_json_iter()),
            [
                '{"comment":"comment","config_file":"config_file",'
                '"file":{"prefix":"/tmp/nodir/@home-","timestamp":"20230213001000"},'
                '"source":"snap_source","trigger":"S"}'
            ],
        )

    def test_all_but_k(self):
        self.assertEqual(list(snap_operator._all_but_last_k([1, 2, 3, 4], 2)), [1, 2])
        self.assertEqual(
            list(snap_operator._all_but_last_k([1, 2, 3, 4], 1)), [1, 2, 3]
        )
        self.assertEqual(
            list(snap_operator._all_but_last_k([1, 2, 3, 4], 0)), [1, 2, 3, 4]
        )
        # Leave -2 out of 4 elements - causes an error.
        with self.assertRaisesRegex(ValueError, r"k = .+ < 0"):
            list(snap_operator._all_but_last_k([1, 2, 3, 4], -2))
        # Leave 5 out of 2 elements. Succeeds.
        self.assertEqual(list(snap_operator._all_but_last_k([1, 2], 5)), [])

    def setUp(self) -> None:
        super().setUp()
        self._exit_stack = contextlib.ExitStack()
        self._exit_stack.enter_context(
            mock.patch.object(
                btrfs_mechanism.BtrfsSnapMechanism,
                "verify_volume",
                lambda self, _: True,
            )
        )
        self._mock_delete = mock.MagicMock()
        self._exit_stack.enter_context(
            mock.patch.object(snap_holder.Snapshot, "delete", self._mock_delete)
        )
        self._mock_create_from = mock.MagicMock()
        self._exit_stack.enter_context(
            mock.patch.object(
                snap_holder.Snapshot, "create_from", self._mock_create_from
            )
        )

        def fake_get_deletes(
            self, now: datetime.datetime, records: list[tuple[datetime.datetime, str]]
        ) -> Iterator[tuple[datetime.datetime, str]]:
            for when, pathname in records:
                if pathname != "":
                    yield when, pathname

        self._exit_stack.enter_context(
            mock.patch.object(
                auto_cleanup_without_ttl.DeleteLogic, "get_deletes", fake_get_deletes
            )
        )
        self._exit_stack.enter_context(
            mock.patch.object(
                snap_operator, "_get_existing_snaps", lambda configs: self._old_snaps
            )
        )

    def tearDown(self) -> None:
        self._exit_stack.close()
        super().tearDown()


if __name__ == "__main__":
    unittest.main()
