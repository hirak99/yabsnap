import dataclasses
import os
import re

from . import common_fs_utils
from .. import os_utils

# Define regex pattern to match a valid `btrfs subvolume list` line
btrfs_pattern = re.compile(r"^ID (\d+) gen (\d+) top level (\d+) path (.+)$")


@dataclasses.dataclass
class _Subvolume:
    id: int
    gen: int
    top_level: int
    # Note: Path varies based on directory passed.
    # It may be relative if a relative path exists.
    # It is best to rely on the basename of path.
    path: str


def _btrfs_list(directory: str):
    # We may switch to using json output, but at the time of writing it is not
    # mature yet. Ref. https://github.com/kdave/btrfs-progs/issues/833
    result = os_utils.execute_sh(f"btrfs subvolume list {directory}")
    assert result is not None

    subvolumes: list[_Subvolume] = []
    for line in result.splitlines():
        match = btrfs_pattern.match(line)
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


# Finds all nested subvolume paths.
# mount_subvol: E.g. "@home".
def _get_nested_subvs(subvolumes: list[_Subvolume], mount_subvol: str):
    # If none, root is mounted; everything is a child directory.
    this_subv_id: int | None = None
    if mount_subvol != "":
        for subv in subvolumes:
            if subv.path == mount_subvol:
                this_subv_id = subv.id
                break
        else:
            raise ValueError(f"Subvolume for {mount_subvol=} not found.")
    by_id = {s.id: s for s in subvolumes}
    nested_directories: list[str] = []
    for subv in subvolumes:
        nested_dir: str | None = None
        while True:
            parent = by_id.get(subv.top_level)
            if parent is None:
                break
            # Since path may or may not be relative, we rely on basename which
            # is a constant wrt path directory queried.
            subv_path_base = os.path.basename(subv.path)
            if nested_dir is None:
                nested_dir = subv_path_base
            else:
                nested_dir = os.path.join(subv_path_base, nested_dir)
            # Root is mounted, and parent is root.
            parent_root_mounted = this_subv_id is None and parent.top_level == 5
            if parent_root_mounted:
                nested_dir = os.path.join(parent.path, nested_dir)
            if (parent_root_mounted or parent.id == this_subv_id) and nested_dir:
                nested_directories.append(nested_dir)
                # Parents of the mounted dir will no longer be mounted, safe to exit early.
                break
            subv = parent
    return sorted(nested_directories)


def get_nested_subvs(directory: str):
    mount_subvol = common_fs_utils.mount_attributes(directory).subvol_name
    mount_subvol = mount_subvol.removeprefix("/")
    subvolumes = _btrfs_list(directory)
    return _get_nested_subvs(subvolumes, mount_subvol)
