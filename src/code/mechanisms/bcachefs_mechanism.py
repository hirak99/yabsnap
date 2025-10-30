import logging
import shlex

from . import abstract_mechanism
from .. import global_flags
from ..utils import os_utils

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
        except os_utils.CommandError:
            logging.error("Unable to create snapshot using bcachefs.")
            raise

    @override
    def delete(self, destination: str):
        try:
            _execute_sh(f"bcachefs subvolume delete {shlex.quote(destination)}")
        except os_utils.CommandError:
            logging.error("Unable to delete snapshot.")
            raise

    @override
    def rollback_gen(
        self,
        source_dests: list[tuple[str, str]],
        live_subvol_map: dict[str, str] | None,
    ) -> list[str]:
        # Rollback would probably be similar to btrfs, but needs to be implemented.
        raise NotImplementedError(
            "Rollback is not yet implemented for bcachefs snapshots."
        )

    @override
    def sync_paths(self, paths: set[str]):
        # If a sync command exists, it should be used here. Otherwise, it can be a no-op.
        pass
