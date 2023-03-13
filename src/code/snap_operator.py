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
import logging
import os

from . import configs
from . import deletion_logic
from . import human_interval
from . import os_utils
from . import snap_holder

from typing import Iterable, Iterator, Optional


def _get_old_backups(config: configs.Config) -> Iterator[snap_holder.Snapshot]:
    """Returns existing backups in chronological order."""
    configdir = os.path.dirname(config.dest_prefix)
    for fname in os.listdir(configdir):
        pathname = os.path.join(configdir, fname)
        if not os.path.isdir(pathname):
            continue
        if not pathname.startswith(config.dest_prefix):
            continue
        yield snap_holder.Snapshot(pathname)


def find_target(config: configs.Config, suffix: str) -> Optional[snap_holder.Snapshot]:
    if len(suffix) < snap_holder.TIME_FORMAT_LEN:
        raise ValueError(
            "Length of snapshot identifier suffix "
            f"must be at least {snap_holder.TIME_FORMAT_LEN}."
        )
    for snap in _get_old_backups(config):
        if snap.target.endswith(suffix):
            return snap_holder.Snapshot(snap.target)
    return None


class SnapOperator:
    def __init__(self, config: configs.Config, now: datetime.datetime) -> None:
        self._config = config
        self._now = now
        self._now_str = self._now.strftime(snap_holder.TIME_FORMAT)
        # Set to true on any delete operation.
        self.need_sync = False

    def _remove_expired(self, snaps: Iterable[snap_holder.Snapshot]) -> bool:
        """Deletes old backups. Returns True if new backup is needed."""
        # Only consider scheduled backups for expiry.
        candidates = [
            (x.snaptime, x.target) for x in snaps if x.metadata.trigger in {"", "S"}
        ]
        # Append a placeholder to denote the backup that will be taken next.
        # If this is deleted, it would indicate not to create new backup.
        candidates.append((self._now, ""))

        delete = deletion_logic.DeleteManager(self._config.deletion_rules)
        for when, target in delete.get_deletes(self._now, candidates):
            if target == "":
                logging.info(f"No new backup needed for {self._config.source}")
                return False
            elapsed_secs = (self._now - when).total_seconds()
            if elapsed_secs > self._config.min_keep_secs:
                snap_holder.Snapshot(target).delete()
                self.need_sync = True
            else:
                logging.info(f"Not enough time passed, not deleting {target}")

        return True

    def _create_and_maintain_n_backups(
        self, count: int, trigger: str, comment: Optional[str]
    ):
        # Find previous snaps.
        # Doing this before the update handles dryrun (where no new snap is created).
        previous_snaps = [
            x for x in _get_old_backups(self._config) if x.metadata.trigger == trigger
        ]

        if count > 0:
            snapshot = snap_holder.Snapshot(self._config.dest_prefix + self._now_str)
            snapshot.metadata.trigger = trigger
            if comment:
                snapshot.metadata.comment = comment
            snapshot.create_from(self._config.source)

        # Clean up old snaps; leave count-1 previous snaps (plus the one now created).
        for expired in previous_snaps[: -count + 1]:
            expired.delete()
            self.need_sync = True

    def create(self, comment: Optional[str]):
        try:
            self._create_and_maintain_n_backups(
                count=self._config.keep_user, trigger="U", comment=comment
            )
        except PermissionError:
            os_utils.eprint(
                f"Could perform snap for {self._config.config_file}; run as root?"
            )

    def on_pacman(self):
        last_snap: Optional[snap_holder.Snapshot] = None
        for snap in _get_old_backups(self._config):
            if snap.metadata.trigger == "I":
                last_snap = snap
        if last_snap is not None:
            time_since = (self._now - last_snap.snaptime).total_seconds()
            if time_since < self._config.preinstall_interval:
                logging.info(
                    f"Only {time_since:0.0f}s has passed since last install, "
                    f"need {self._config.preinstall_interval:0.0f}s. Skipping."
                )
                return
        self._create_and_maintain_n_backups(
            count=self._config.keep_preinstall,
            trigger="I",
            comment=os_utils.last_pacman_command(),
        )

    def scheduled(self):
        """Triggers periodically by the system timer."""
        previous_snaps = list(_get_old_backups(self._config))
        if previous_snaps:
            # Check if we should trigger a backup.
            wait_until = (
                previous_snaps[-1].snaptime
                + datetime.timedelta(seconds=self._config.trigger_interval)
                - configs.DURATION_BUFFER
            ) - self._now
            if wait_until.total_seconds() > 0:
                logging.info(
                    f"Schedule not triggered for {self._config.source}, need to wait {wait_until}"
                )
                return
        # Manage deletions and check if new backup is needed.
        need_new = self._remove_expired(previous_snaps)
        if need_new:
            snapshot = snap_holder.Snapshot(self._config.dest_prefix + self._now_str)
            snapshot.metadata.trigger = "S"
            snapshot.create_from(self._config.source)

    def list_backups(self):
        for snap in _get_old_backups(self._config):
            trigger_str = "".join(
                c if snap.metadata.trigger == c else " " for c in "SIU"
            )
            print(f"{trigger_str}  ", end="")
            print(f"{snap.target}  ", end="")
            # print(f'{snap.snaptime}  ', end='')
            elapsed = (self._now - snap.snaptime).total_seconds()
            elapsed_str = "(" + human_interval.humanize(elapsed) + " ago)"
            print(f"{elapsed_str:<20}  ", end="")
            print(snap.metadata.comment)
        print("")
