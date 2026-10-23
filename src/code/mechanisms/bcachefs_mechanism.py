import logging
import os
import shlex

from .. import global_flags
from ..utils import mtab_parser
from ..utils import os_utils
from . import abstract_mechanism

from typing import override


def _execute_sh(cmd: str):
    if global_flags.FLAGS.dryrun:
        os_utils.eprint("Would run " + cmd)
    else:
        os_utils.runsh_or_error(cmd)


# NOTE: This is implementation is untested.
class BcachefsSnapMechanism(abstract_mechanism.SnapMechanism):
    @override
    def verify_volume(self, source: str) -> bool:
        # Check if the mount point is a bcachefs filesystem.
        fstype = os_utils.runsh("stat -f --format=%T " + source)
        if not fstype:
            logging.warning(f"Not bcachefs (cannot determine filesystem): {source}")
            return False
        if fstype.strip() != "bcachefs":
            logging.warning(f"Not bcachefs (filesystem not bcachefs): {source}")
            return False
        return True

    @override
    def create(self, source: str, destination: str):
        logging.warning("BCACHEFS support is at a very early stage and experimental.")
        if not os_utils.command_exists("bcachefs"):
            raise RuntimeError(
                "bcachefs not found, please install to create bcachefs snapshots"
            )
        try:
            _execute_sh(
                f"bcachefs subvolume snapshot {shlex.quote(source)} {shlex.quote(destination)}"
            )
        except os_utils.CommandError as exc:
            raise RuntimeError("Unable to create; are you running as root?") from exc

    @override
    def delete(self, destination: str):
        try:
            _execute_sh(f"bcachefs subvolume delete {shlex.quote(destination)}")
        except os_utils.CommandError as exc:
            raise RuntimeError("Unable to delete; are you running as root?") from exc

    @override
    def _nested_dest_reason(self, source: str, dest_prefix: str) -> str | None:
        destdir = os.path.dirname(dest_prefix.rstrip("/"))
        if not destdir:
            return None
        if not abstract_mechanism.destdir_inside_source(source, dest_prefix):
            return None
        # Path-inside is not enough: a separately mounted snapshots subvolume
        # (the recommended layout) is path-inside but safe. Only warn when both
        # resolve to the same mount (i.e. no separate mount in between).
        try:
            src_entry = mtab_parser.mount_entry_for(os.path.normpath(source))
            dst_entry = mtab_parser.mount_entry_for(os.path.normpath(destdir))
        except Exception as exc:  # Never break snapshot creation on a warning.
            logging.debug(f"Skipping nested-dest check for {source!r}: {exc}")
            return None
        if src_entry is None or dst_entry is None:
            return None
        if dst_entry.device != src_entry.device:
            return None
        if len(dst_entry.mtab_mount_pt) > len(src_entry.mtab_mount_pt):
            return None  # Snapshot storage is separately mounted; safe.
        return (
            f"snapshot storage {destdir!r} is inside the source {source!r} on the same mount; "
            "move `dest_prefix` to a separately mounted location"
        )

    @override
    def rollback_gen(
        self,
        snapshots: list[abstract_mechanism.LightSnapshot],
        subvol_map: dict[str, str] | None,
    ) -> list[str]:
        # Rollback would probably be similar to btrfs, but needs to be implemented.
        raise NotImplementedError(
            "Rollback is not yet implemented for bcachefs snapshots."
        )

    @override
    def sync_paths(self, paths: set[str]):
        # If a sync command exists, it should be used here. Otherwise, it can be a no-op.
        pass
