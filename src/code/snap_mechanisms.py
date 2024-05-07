import abc
import enum
import functools
import logging

from . import global_flags
from . import os_utils

# TODO: Move btrfs based rollback to this abstraction.
# TODO: Move btrfs sync to this abstraction.

# The type of snapshot is maintained in two places -
# 1. Config
# 2. Snapshot
class SnapType(enum.Enum):
    UNKNOWN = "UNKNOWN"
    BTRFS = "BTRFS"


class SnapMechanism(abc.ABC):
    """Interface with necessary methods to implement snapshotting system.

    Example implementations may be based on btrfs, rsync, bcachefs, etc.
    """
    @abc.abstractmethod
    def verify_volume(self, mount_point: str) -> bool:
        pass

    @abc.abstractmethod
    def create(self, source: str, destination: str):
        pass

    @abc.abstractmethod
    def delete(self, destination: str):
        pass


def _execute_sh(cmd: str):
    if global_flags.FLAGS.dryrun:
        os_utils.eprint("Would run " + cmd)
    else:
        os_utils.execute_sh(cmd)


class _BtrfsSnapMechanism(SnapMechanism):
    # @staticmethod
    # def sync(mount_paths: set[str]) -> None:
    #     for mount_path in sorted(mount_paths):
    #         if global_flags.FLAGS.dryrun:
    #             os_utils.eprint(f"Would sync {mount_path}")
    #             continue
    #         os_utils.eprint("Syncing ...", flush=True)
    #         os_utils.execute_sh(f"btrfs subvolume sync {mount_path}")

    def verify_volume(self, mount_point: str) -> bool:
        # Based on https://stackoverflow.com/a/32865333/196462
        fstype = os_utils.execute_sh(
            "stat -f --format=%T " + mount_point, error_ok=True
        )
        if not fstype:
            logging.warning(f"Not btrfs (cannot determine filesystem): {mount_point}")
            return False
        if fstype.strip() != "btrfs":
            logging.warning(f"Not btrfs (filesystem not btrfs): {mount_point}")
            return False
        inodenum = os_utils.execute_sh("stat --format=%i " + mount_point, error_ok=True)
        if not inodenum:
            logging.warning(f"Not btrfs (cannot determine inode): {mount_point}")
            return False
        if inodenum.strip() != "256":
            logging.warning(
                f"Not btrfs (inode not 256, possibly a subdirectory of a btrfs mount): {mount_point}"
            )
            return False
        return True

    def create(self, source: str, destination: str):
        try:
            _execute_sh("btrfs subvolume snapshot -r " f"{source} {destination}")
        except os_utils.CommandError:
            logging.error("Unable to create; are you running as root?")
            raise

    def delete(self, destination: str):
        try:
            _execute_sh(f"btrfs subvolume delete {destination}")
        except os_utils.CommandError:
            logging.error("Unable to delete; are you running as root?")
            raise


@functools.cache
def get(snap_type: SnapType) -> SnapMechanism:
    """Singleton implementation."""
    if snap_type == SnapType.BTRFS:
        return _BtrfsSnapMechanism()
    raise RuntimeError(f"Unknown snap_type {snap_type}")
