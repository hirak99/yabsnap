import dataclasses
import functools


@dataclasses.dataclass
class _MountAttributes:
    # The device e.g. /mnt/volume/subv under which we have the subv or its parent is mounted.
    device: str
    # E.g. '/@' or '/@home'.
    subvol_name: str


@functools.cache
def _mtab_contents() -> list[str]:
    with open("/etc/mtab") as f:
        return f.readlines()


@functools.cache
def mount_attributes(mount_point: str) -> _MountAttributes:
    # For a mount point, this denotes the longest path that was seen in /etc/mtab.
    # This is therefore the point where that directory is mounted.
    longest_match_to_mount_point = ""
    # Which line matches the mount point.
    matched_line: str = ""
    for this_line in _mtab_contents():
        this_tokens = this_line.split()
        if mount_point.startswith(this_tokens[1]):
            if len(this_tokens[1]) > len(longest_match_to_mount_point):
                longest_match_to_mount_point = this_tokens[1]
                matched_line = this_line

    if not matched_line:
        raise ValueError(f"Mount point not found: {mount_point}")
    tokens = matched_line.split()

    if tokens[2] != "btrfs":
        raise ValueError(f"Mount point is not btrfs: {mount_point} ({tokens[2]})")
    mount_param: str = ""
    for mount_param in tokens[3].split(","):
        subvol_prefix = "subvol="
        if mount_param.startswith(subvol_prefix):
            break
    else:
        raise RuntimeError(f"Could not find subvol= in {matched_line!r}")
    subvol_name = mount_param[len(subvol_prefix) :]
    if tokens[1] != mount_point:
        nested_subvol = mount_point.removeprefix(tokens[1])
        assert nested_subvol.startswith("/")
        subvol_name = nested_subvol
    return _MountAttributes(device=tokens[0], subvol_name=subvol_name)
