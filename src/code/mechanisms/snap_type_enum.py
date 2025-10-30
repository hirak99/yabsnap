import enum


# The type of snapshot is maintained in two places -
# 1. Config
# 2. Snapshot
class SnapType(enum.Enum):
    UNKNOWN = "UNKNOWN"
    BTRFS = "BTRFS"
    RSYNC = "RSYNC"
    BCACHEFS = "BCACHEFS"
