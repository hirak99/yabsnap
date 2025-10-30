# Copyright 2025 Nomen Aliud (aka Arnab Bose)
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
import unittest

from . import scheduled_snapshot_ttl
from ..utils import human_interval

_HOUR = 60 * 60
_DAY = 24 * _HOUR
_WEEK = 7 * _DAY


def _simulate_long_run(
    rules: dict[str, int],
    how_long_to_run: datetime.timedelta,
    every: datetime.timedelta = datetime.timedelta(minutes=30),
):
    starting_now = datetime.datetime.strptime("2025-01-01", r"%Y-%m-%d")
    index = 0
    mgr = scheduled_snapshot_ttl.CreationTimeTtl(
        [
            (datetime.timedelta(seconds=human_interval.parse_to_secs(k)), v)
            for k, v in rules.items()
        ]
    )
    existing_snaps: list[tuple[datetime.datetime, float | None]] = []
    created_ttls = []
    while index * every < how_long_to_run:
        now = starting_now + index * every
        ttl_secs = mgr.ttl_of_new_snapshot(now, existing_snaps)
        if ttl_secs is not None:
            created_ttls.append(((index * every).total_seconds(), ttl_secs))
            expiry = now.timestamp() + ttl_secs
            existing_snaps.append((now, expiry))
        index += 1
    # Return ints to make the test output look nicer, as we will only use
    # integer-seconds for tests.
    return [(int(x), int(y)) for x, y in created_ttls]


class SnapOperatorTest(unittest.TestCase):
    def test_empty_ruleset(self):
        result = _simulate_long_run(
            rules={}, how_long_to_run=datetime.timedelta(days=3)
        )
        self.assertEqual(
            result,
            [],
        )

    def test_simulate_single_rule(self):
        result = _simulate_long_run(
            rules={"1 day": 1}, how_long_to_run=datetime.timedelta(days=3)
        )
        self.assertEqual(
            result,
            [
                (0 * _DAY, 1 * _DAY),
                (1 * _DAY, 1 * _DAY),
                (2 * _DAY, 1 * _DAY),
            ],
        )

        result = _simulate_long_run(
            rules={"1 day": 2}, how_long_to_run=datetime.timedelta(days=8)
        )
        self.assertEqual(
            result,
            [
                (0 * _DAY, 2 * _DAY),
                (1 * _DAY, 2 * _DAY),
                (2 * _DAY, 2 * _DAY),
                (3 * _DAY, 2 * _DAY),
                (4 * _DAY, 2 * _DAY),
                (5 * _DAY, 2 * _DAY),
                (6 * _DAY, 2 * _DAY),
                (7 * _DAY, 2 * _DAY),
            ],
        )

        result = _simulate_long_run(
            rules={"1 week": 2}, how_long_to_run=datetime.timedelta(days=8)
        )
        self.assertEqual(
            result,
            [
                (0 * _WEEK, 2 * _WEEK),
                (1 * _WEEK, 2 * _WEEK),
            ],
        )

    def test_simulate_mixed_rules(self):
        result = _simulate_long_run(
            rules={"1 week": 1, "1 day": 1}, how_long_to_run=datetime.timedelta(days=4)
        )
        self.assertEqual(
            result,
            [
                (0 * _WEEK, 1 * _WEEK),
                (1 * _DAY, 1 * _DAY),
                (2 * _DAY, 1 * _DAY),
                (3 * _DAY, 1 * _DAY),
            ],
        )

        result = _simulate_long_run(
            rules={"1 week": 2, "1 day": 2}, how_long_to_run=datetime.timedelta(days=16)
        )
        self.assertEqual(
            result,
            [
                (0 * _WEEK, 2 * _WEEK),
                (1 * _DAY, 2 * _DAY),
                (2 * _DAY, 2 * _DAY),
                (3 * _DAY, 2 * _DAY),
                (4 * _DAY, 2 * _DAY),
                (5 * _DAY, 2 * _DAY),
                (6 * _DAY, 2 * _DAY),
                (7 * _DAY, 2 * _WEEK),
                (8 * _DAY, 2 * _DAY),
                (9 * _DAY, 2 * _DAY),
                (10 * _DAY, 2 * _DAY),
                (11 * _DAY, 2 * _DAY),
                (12 * _DAY, 2 * _DAY),
                (13 * _DAY, 2 * _DAY),
                (14 * _DAY, 2 * _WEEK),
                (15 * _DAY, 2 * _DAY),
            ],
        )

        result = _simulate_long_run(
            # Test of completely overlapping rules.
            # Hourly 3 snaps takes precedence over 2-hourly 1 snap.
            rules={"2 hour": 1, "1 hour": 3},
            how_long_to_run=datetime.timedelta(hours=6),
        )
        self.assertEqual(
            result,
            [
                (0 * _HOUR, 3 * _HOUR),
                (1 * _HOUR, 3 * _HOUR),
                (2 * _HOUR, 3 * _HOUR),
                (3 * _HOUR, 3 * _HOUR),
                (4 * _HOUR, 3 * _HOUR),
                (5 * _HOUR, 3 * _HOUR),
            ],
        )
