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

"""
Logic to assign TTL to snapshots at the time of scheduled creation.

This module assigns a Time-To-Live (TTL) to snapshots that are created on schedule.
It uses configuration rules (e.g., keep_hourly, keep_daily) to determine the appropriate
TTL, ensuring compliance with user-defined retention policies.

Additionally, it determines whether a snapshot should be created based on the defined schedule.
"""

import datetime

from .. import configs

# Since the scheduled time is not perfect, we leave a bit of buffer for all time
# comparisons. This makes the TTL generation algorithm more robust by preventing
# inequality discontinuities.
_EPSILON = configs.DURATION_BUFFER


class CreationTimeTtl:
    def __init__(self, rules: list[tuple[datetime.timedelta, int]]) -> None:
        self._rules = rules

    def ttl_of_new_snapshot(
        self,
        now: datetime.datetime,
        existing_creation_expiries: list[tuple[datetime.datetime, float | None]],
    ) -> int | None:
        """Returns None if nothing needs to be created, or TTL if a new record is needed.

        Args:
            now: The current time, or when processing began.
            existing_snaps: A list of all snaps that are present. We only use the expiry field.
        """
        snapshot_ttl = datetime.timedelta.min
        for period, n in self._rules:
            skip_creation = False
            count_at_next_time = 0
            for created, expiry_ts in existing_creation_expiries:
                if expiry_ts is None:
                    # Snap does not have TTL.
                    continue
                expiry = datetime.datetime.fromtimestamp(expiry_ts)
                duration = expiry - created
                if duration < period - _EPSILON:
                    # Snap is too short for the current rule.
                    continue
                if now - created < period - _EPSILON:
                    # The last one was created recently. Do not create a new snap.
                    skip_creation = True
                    break
                if expiry - now <= period + _EPSILON:
                    # The snap will be deleted on next period.
                    continue
                if created <= now - period * n + _EPSILON:
                    # Too old.
                    continue
                count_at_next_time += 1

            if not skip_creation:
                if count_at_next_time < n:
                    snapshot_ttl = max(snapshot_ttl, period * n)

        if snapshot_ttl == datetime.timedelta.min:
            return None

        return int(snapshot_ttl.total_seconds())
