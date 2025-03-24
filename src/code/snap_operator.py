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
import logging
import os

from . import auto_cleanup_without_ttl
from . import configs
from . import global_flags
from . import human_interval
from . import os_utils
from . import scheduled_snapshot_ttl
from . import snap_holder

from typing import Any, Iterator, Optional, TypeVar


def _get_existing_snaps(config: configs.Config) -> Iterator[snap_holder.Snapshot]:
    """Returns existing backups in chronological order."""
    destdir = os.path.dirname(config.dest_prefix)

    if not os.path.isdir(destdir):
        os_utils.fatal_error(
            f"Please create {destdir=}, referred in {config.config_file}."
        )
    if not os.access(destdir, os.R_OK):
        os_utils.fatal_error(
            f"Error accessing {destdir=}, referred in {config.config_file}."
        )

    for fname in os.listdir(destdir):
        pathname = os.path.join(destdir, fname)
        if not os.path.isdir(pathname):
            continue
        if not pathname.startswith(config.dest_prefix):
            continue
        try:
            yield snap_holder.Snapshot(pathname)
        except ValueError:
            logging.warning(f"Could not parse timestamp, ignoring: {pathname}")


def find_target(config: configs.Config, suffix: str) -> Optional[snap_holder.Snapshot]:
    if len(suffix) < global_flags.TIME_FORMAT_LEN:
        raise ValueError(
            "Length of snapshot identifier suffix "
            f"must be at least {global_flags.TIME_FORMAT_LEN}."
        )
    for snap in _get_existing_snaps(config):
        if snap.target.endswith(suffix):
            return snap_holder.Snapshot(snap.target)
    return None


_GenericT = TypeVar("_GenericT")


def _all_but_last_k(array: list[_GenericT], k: int) -> Iterator[_GenericT]:
    """All but at most k last elements."""
    # Edge cases -
    #   k > len(array): Returns empty array.
    #   k < 0: Error.
    if k < 0:
        raise ValueError(f"k = {k} < 0")
    yield from array[: len(array) - k]


class SnapOperator:
    def __init__(self, config: configs.Config, now: datetime.datetime) -> None:
        self._config = config
        self._now = now
        self._now_str = self._now.strftime(global_flags.TIME_FORMAT)
        # Set to true on any create operation.
        self.snaps_created = False
        # Set to true on any delete operation. If True, may run a btrfs subv sync.
        self.snaps_deleted = False
        # Temporarily holds all snaps to delete on scheduled().
        # This enables the actual operation of deleting them to happen at the end.
        self._scheduled_to_delete: list[snap_holder.Snapshot] = []

    # Part of scheduled().
    def _delete_expired_ttl(
        self, snaps: list[snap_holder.Snapshot]
    ) -> list[snap_holder.Snapshot]:
        """Deletes snapshots with expired TTL, returns _remaining_ snapshots."""
        remaining: list[snap_holder.Snapshot] = []
        for snap in snaps:
            if snap.metadata.is_expired(self._now):
                logging.info(f"Expired snapshot: {snap.target}")
                self._scheduled_to_delete.append(snap)
            else:
                remaining.append(snap)
        return remaining

    # Part of scheduled().
    def _get_scheduled_snapshot_ttl(
        self, snaps: list[snap_holder.Snapshot]
    ) -> tuple[bool, int]:
        """If scheduled snapshot ttl is enabled, carry out the TTL logic.

        Returns:
          bool: Whether a new snapshot will be made.
          int: What should be the TTL in secods. If 0 or less, no TTL will be applied.
        """
        if self._config.enable_scheduled_ttl:
            # Note: deletion_rules subtract the buffer time. That's needed so
            # that on schedule, the TTL's expire and get deleted.
            mgr = scheduled_snapshot_ttl.CreationTimeTtl(self._config.deletion_rules)
            ttl_of_new_snap = mgr.ttl_of_new_snapshot(
                now=self._now,
                existing_creation_expiries=[
                    (x.snaptime, x.metadata.expiry) for x in snaps
                ],
            )
            if ttl_of_new_snap is not None:
                return True, ttl_of_new_snap
        return False, 0

    # Part of scheduled().
    def _non_ttl_scheduled_deletion(self, snaps: list[snap_holder.Snapshot]) -> bool:
        """Applies deletion logic for scheduled backups without TTL.

        Returns:
            True iff a new snapshot should be created.
        """
        candidates = [
            (x.snaptime, x.target) for x in snaps if x.metadata.trigger in {"", "S"}
        ]
        # Append a placeholder to denote the backup that will be taken next.
        # If this is deleted, it would indicate not to create new backup.
        candidates.append((self._now, ""))

        delete_logic = auto_cleanup_without_ttl.DeleteLogic(self._config.deletion_rules)
        for when, target in delete_logic.get_deletes(self._now, candidates):
            if target == "":
                logging.info(f"No new backup needed for {self._config.source}")
                return False
            elapsed_secs = (self._now - when).total_seconds()
            if elapsed_secs > self._config.min_keep_secs:
                snap = snap_holder.Snapshot(target)
                if snap.metadata.expiry is None:
                    self._scheduled_to_delete.append(snap_holder.Snapshot(target))
                else:
                    # Note: It will eventually get deleted, we just need to wait until TTL.
                    logging.info(f"Refusing to clean up target with TTL: {target}")
            else:
                logging.info(f"Not enough time passed, not deleting {target}")

        return True

    # Part of scheduled().
    def _scheduled_deletion_and_creation(
        self, snaps: list[snap_holder.Snapshot]
    ) -> tuple[bool, int]:
        """Deletes old backups. Returns True if new backup is needed.

        Returns:
          bool: Whether a new snapshot will be made.
          int: What should be the TTL in seconds. If 0 or less, no TTL will be applied.
        """

        # Handle snapshots with TTL.
        need_new, ttl_secs = self._get_scheduled_snapshot_ttl(snaps)
        if not need_new and ttl_secs != 0:
            # Unexpected. Possible logical error somewhere.
            logging.warning(f"BUG DETECTED, {need_new=}, {ttl_secs=}")

        # Handle snapshots without TTL.
        if not self._non_ttl_scheduled_deletion(snaps):
            # Non scheduled-ttl deletion completed, does not require a new snap creation.
            # Should still create one if scheduled logic wanted one.
            return need_new, ttl_secs

        # If we are here, non-ttl deletion logic wants to create a new snapshot.
        return True, ttl_secs if need_new else 0

    # Part of scheduled().
    def _manage_scheduled_lifecycle(self, snaps: list[snap_holder.Snapshot]):
        wait_until = self._next_trigger_time(snaps)
        if wait_until is not None:
            if self._now <= wait_until - configs.DURATION_BUFFER:
                logging.info(
                    f"Already triggered for {self._config.source}, wait until {wait_until}"
                )
                return

        # Manage deletions and check if new backup is needed.
        need_new, ttl_secs = self._scheduled_deletion_and_creation(snaps)
        if need_new:
            snapshot = snap_holder.Snapshot(self._config.dest_prefix + self._now_str)
            snapshot.metadata.trigger = "S"
            if ttl_secs > 0:
                snapshot.metadata.expiry = int(self._now.timestamp()) + ttl_secs
            snapshot.create_from(self._config.snap_type, self._config.source)
            self.snaps_created = True

    def _create_and_maintain_n_backups(
        self, count: int, trigger: str, comment: Optional[str]
    ):
        logging.info(f"Maintain {count} volumes of type {trigger}.")
        if not self._config.is_compatible_volume():
            logging.warning(f"Not a compatible volume {self._config.source}.")
            return
        # Find previous snaps.
        # Doing this before the update handles dryrun (where no new snap is created).
        previous_snaps = [
            x
            for x in _get_existing_snaps(self._config)
            if x.metadata.trigger == trigger
        ]

        if count > 0:
            # From previously existing snaps, leave count - 1 snaps (since we
            # will create one more).
            n_snaps_to_leave = count - 1
            # Create a new snap.
            snapshot = snap_holder.Snapshot(self._config.dest_prefix + self._now_str)
            snapshot.metadata.trigger = trigger
            if comment:
                snapshot.metadata.comment = comment
            snapshot.create_from(self._config.snap_type, self._config.source)
            self.snaps_created = True
        else:
            # From existing snaps, delete all.
            n_snaps_to_leave = 0

        # Clean up old snaps.
        for expired in _all_but_last_k(previous_snaps, n_snaps_to_leave):
            expired.delete()
            self.snaps_deleted = True

    def create(self, comment: Optional[str]):
        try:
            self._create_and_maintain_n_backups(
                count=self._config.keep_user, trigger="U", comment=comment
            )
        except PermissionError:
            os_utils.eprint(
                f"Could not perform snap for {self._config.config_file}; run as root?"
            )
            raise

    def on_pacman(self):
        last_snap: Optional[snap_holder.Snapshot] = None
        for snap in _get_existing_snaps(self._config):
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

    def _next_trigger_time(
        self, scheduled_snaps: list[snap_holder.Snapshot]
    ) -> Optional[datetime.datetime]:
        """Returns the next time after which a scheduled backup can trigger."""
        if not scheduled_snaps:
            return None
        # Check if we should trigger a backup.
        # Phase of the time windows. Optionally, we can set it to phase = time.timezone.
        # Then the times will align to the local timezone. However, DST messes it up;
        # so we just choose phase = 0 or UTC.
        phase = 0
        previous_mod = (
            scheduled_snaps[-1].snaptime - datetime.timedelta(seconds=phase)
        ).timestamp() // self._config.trigger_interval
        wait_until = datetime.datetime.fromtimestamp(
            (previous_mod + 1) * self._config.trigger_interval + phase
        )
        return wait_until

    def scheduled(self):
        """Triggers periodically by the system timer."""
        if not self._config.is_compatible_volume():
            # There is some kind of mismatch, for example the directory is not btrfs.
            # A warning should already be printed by the check implementation.
            # Another warning here in case it is missed in the code for any reason.
            logging.warning("Incompatible volume")
            return

        # Hold everything to be deleted, so that we delete at the end of scheduled().
        self._scheduled_to_delete = []

        # Delete expired snaps with TTL. Carry out irrespective of the waiting time.
        snaps = list(_get_existing_snaps(self._config))
        snaps = self._delete_expired_ttl(snaps)

        # All _scheduled_ snaps that will remain.
        scheduled_snaps = [x for x in snaps if "S" in x.metadata.trigger]

        self._manage_scheduled_lifecycle(scheduled_snaps)

        for snap in self._scheduled_to_delete:
            snap.delete()
            self.snaps_deleted = True

    def list_snaps(self):
        """Print the backups for humans."""
        print(f"Config: {self._config.config_file} (source={self._config.source})")
        # Just display the log if it's not a btrfs volume.
        _ = self._config.is_compatible_volume()
        print(f"Snaps at: {self._config.dest_prefix}...")
        for snap in _get_existing_snaps(self._config):
            columns: list[str] = []
            columns.append("  " + snap.target.removeprefix(self._config.dest_prefix))
            trigger_str = "".join(
                c if snap.metadata.trigger == c else " " for c in "SIU"
            )
            columns.append(trigger_str)
            # print(f'{snap.snaptime}  ', end='')
            elapsed = (self._now - snap.snaptime).total_seconds()
            elapsed_str = "(" + human_interval.humanize(elapsed) + " ago)"
            columns.append(f"{elapsed_str:<20}")

            ttl_str = ""
            if snap.metadata.expiry is not None:
                ttl = snap.metadata.expiry - self._now.timestamp()
                ttl_str = "TTL: " + human_interval.humanize(ttl)
            columns.append(f"{ttl_str:<18}")

            columns.append(snap.metadata.comment)
            print("  ".join(columns))
        print("")

    def _snaps_json_iter(self) -> Iterator[str]:
        result: dict[str, Any] = {
            "config_file": self._config.config_file,
            "source": self._config.source,
        }
        # Just display the log if it's not a btrfs volume.
        _ = self._config.is_compatible_volume()
        result["file"] = {"prefix": self._config.dest_prefix}
        for snap in _get_existing_snaps(self._config):
            result["file"]["timestamp"] = snap.target.removeprefix(
                self._config.dest_prefix
            )
            result.update(snap.as_json())
            yield json.dumps(result, sort_keys=True, separators=(",", ":"))

    def list_snaps_json(self):
        """Print snaps for machine readable code."""
        for line in self._snaps_json_iter():
            print(line)
