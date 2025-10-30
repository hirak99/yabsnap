import dataclasses
import logging
import re
import shlex

from . import mtab_parser
from . import os_utils


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
    result = os_utils.runsh_or_error(f"btrfs subvolume list {shlex.quote(directory)}")
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
    mount_attrs = mtab_parser.mount_attributes(directory)
    try:
        subvolumes = _btrfs_list(directory)
    except os_utils.CommandError:
        if not os_utils.is_sudo():
            logging.warning(
                f"Cannot check for nested subvolumes in {directory!r}. Run with sudo to check."
            )
            return []
        raise
    return _get_nested_subvs(subvolumes, mount_attrs.subvol_id)
