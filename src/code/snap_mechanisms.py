import enum
import functools

from . import global_flags
from . import os_utils


# The type of snapshot is maintained in two places -
# 1. Config
# 2. Snapshot
class SnapType(enum.Enum):
    BTRFS = "BTRFS"


class _BtrfsSnapshotter:
    @staticmethod
    def sync(mount_paths: set[str]) -> None:
        for mount_path in sorted(mount_paths):
            if global_flags.FLAGS.dryrun:
                os_utils.eprint(f"Would sync {mount_path}")
                continue
            os_utils.eprint("Syncing ...", flush=True)
            os_utils.execute_sh(f"btrfs subvolume sync {mount_path}")


@functools.cache
def get() -> _BtrfsSnapshotter:
    """Singleton implementation."""
    return _BtrfsSnapshotter()
