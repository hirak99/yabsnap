import dataclasses
import functools

from .. import os_utils


@dataclasses.dataclass
class _MountAttributes:
    # The device e.g. /mnt/volume/subv under which we have the subv or its parent is mounted.
    device: str
    # E.g. '/@' or '/@home'.
    subvol_name: str
    # # E.g. 282.
    subvol_id: int


@functools.cache
def _mounts() -> list[str]:
    result = os_utils.execute_sh("mount")
    assert result is not None
    return result.splitlines()


def _get_mtab_param(*, key: str, all_params: str) -> str:
    """Parses a string of the form 'a=b,c=d,e=f' and returns the value for given key."""
    subvol_prefix = f"{key}="
    for mount_param in all_params.split(","):
        if mount_param.startswith(subvol_prefix):
            break
    else:
        raise RuntimeError(f"Could not find {subvol_prefix} in {all_params!r}")
    param_value = mount_param[len(subvol_prefix) :]
    return param_value


@dataclasses.dataclass
class _MountLineTokens:
    device: str
    mount_pt: str
    fs: str
    params: str


def _parse_mount_line(line: str) -> _MountLineTokens:
    tokens = line.split()
    if (tokens[1], tokens[3]) != ("on", "type") or len(tokens) != 6:
        raise ValueError(f"Unexpected - Invalid mount line: {line!r}")
    if not (tokens[5].startswith("(") and tokens[5].endswith(")")):
        raise ValueError(f"Unexpected - mount params not parenthesized: {line!r}")
    return _MountLineTokens(
        device=tokens[0],
        mount_pt=tokens[2],
        fs=tokens[4],
        params=tokens[5].removeprefix("(").removesuffix(")"),
    )


@functools.cache
def mount_attributes(mount_point: str) -> _MountAttributes:
    # For a mount point, this denotes the longest path that was seen in /etc/mtab.
    # This is therefore the point where that directory is mounted.
    longest_match_to_mount_point = ""
    # Which line matches the mount point.
    matched_line: str = ""
    for this_line in _mounts():
        this_tokens = _parse_mount_line(this_line)
        if this_tokens.fs == "autofs":
            # For autofs, another entry should exist which as "btrfs".
            # See also #54.
            continue
        if mount_point.startswith(this_tokens.mount_pt):
            if len(this_tokens.mount_pt) > len(longest_match_to_mount_point):
                longest_match_to_mount_point = this_tokens.mount_pt
                matched_line = this_line

    if not matched_line:
        raise ValueError(f"Mount point not found: {mount_point}")
    tokens = _parse_mount_line(matched_line)

    if tokens.fs != "btrfs":
        raise ValueError(f"Mount point is not btrfs: {mount_point} ({tokens.fs})")

    subvol_name = _get_mtab_param(key="subvol", all_params=tokens.params)
    subvol_id = int(_get_mtab_param(key="subvolid", all_params=tokens.params))

    if tokens.mount_pt != mount_point:
        nested_subvol = mount_point.removeprefix(tokens.mount_pt)
        if not nested_subvol.startswith("/"):
            raise ValueError()
        assert nested_subvol.startswith("/")
        subvol_name = nested_subvol
    return _MountAttributes(
        device=tokens.device, subvol_name=subvol_name, subvol_id=subvol_id
    )
