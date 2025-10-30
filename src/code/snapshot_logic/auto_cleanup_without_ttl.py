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

"""
Logic to determine which snapshots will be cleaned up on schedule, ignoring TTL.

This module identifies snapshots that should be cleaned up based on configuration rules
and a predefined schedule. Snapshots with TTL will not be deleted until the TTL expires,
even if they are included in the cleanup list.

For an alternative mechanism for assigning TTL to snapshots, refer to `creation_time_ttl.py`,
which handles TTL assignment at the time of snapshot creation.
"""

import datetime

from typing import Iterator


class DeleteLogic:
    def __init__(self, rules: list[tuple[datetime.timedelta, int]]) -> None:
        self._rules = rules

    def _required_intervals(
        self, now: datetime.datetime
    ) -> list[tuple[datetime.datetime, datetime.datetime]]:
        result: list[tuple[datetime.datetime, datetime.datetime]] = []
        for width, count in self._rules:
            for index in range(count):
                result.append((now - (index + 1) * width, now - index * width))
        return result

    def get_deletes(
        self, now: datetime.datetime, records: list[tuple[datetime.datetime, str]]
    ) -> Iterator[tuple[datetime.datetime, str]]:
        # We want at least one per each interval.
        intervals = self._required_intervals(now)

        prev_time = None

        for time, fname in records:
            # Check that snaps passed to check are in ascending order, because this is
            # assumed in the deletion logic.
            if prev_time is not None and prev_time > time:
                raise ValueError(f"Records not in order, {prev_time}, {time}")
            else:
                prev_time = time

            # Ensure times are in past.
            if now < time:
                raise ValueError(f"Record time is in the future, {time} > {now}")

            keep = False
            remaining_intervals: list[tuple[datetime.datetime, datetime.datetime]] = []
            for interval in intervals:
                if interval[0] < time <= interval[1]:
                    keep = True
                else:
                    remaining_intervals.append(interval)
            intervals = remaining_intervals
            if keep:
                continue
            yield time, fname
