import dataclasses
import re

from . import common_fs_utils
from .. import os_utils


@dataclasses.dataclass
class _Subvolume:
    id: int
    gen: int
    top_level: int
    # Note: Path varies based on directory passed.
    # It may be relative if a relative path exists.
    path: str


def _parse_btrfs_list(output: str) -> list[_Subvolume]:
    subvolumes: list[_Subvolume] = []
    for line in output.splitlines():
        match = re.match(r"^ID (\d+) gen (\d+) top level (\d+) path (.+)$", line)
        if match:
            subvolumes.append(
                _Subvolume(
                    id=int(match.group(1)),
                    gen=int(match.group(2)),
                    top_level=int(match.group(3)),
                    path=match.group(4),
                )
            )

    return subvolumes


def _btrfs_list(directory: str) -> list[_Subvolume]:
    # We may switch to using json output, but at the time of writing it is not
    # mature yet. Ref. https://github.com/kdave/btrfs-progs/issues/833
    result = os_utils.execute_sh(f"btrfs subvolume list {directory}")
    assert result is not None
    return _parse_btrfs_list(result)


# Finds all nested subvolume paths.
def _get_nested_subvs(subvolumes: list[_Subvolume], subv_id: int) -> list[str]:
    nested_dirs: list[str] = []
    for subv in subvolumes:
        if subv.top_level == subv_id:
            # Assume `btrfs subv list .` was invoked from the same directory as subv_id.
            nested_dirs.append(subv.path)
    return sorted(nested_dirs)


def get_nested_subvs(directory: str) -> list[str]:
    mount_attrs = common_fs_utils.mount_attributes(directory)
    subvolumes = _btrfs_list(directory)
    return _get_nested_subvs(subvolumes, mount_attrs.subvol_id)
