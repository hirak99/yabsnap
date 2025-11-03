import dataclasses
import functools
import logging
import os

from ..utils import os_utils


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
    result = os_utils.runsh_or_error("mount")
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
    mtab_mount_pt: str
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
        mtab_mount_pt=tokens[2],
        fs=tokens[4],
        params=tokens[5].removeprefix("(").removesuffix(")"),
    )


@functools.cache
def mount_attributes(mount_point: str) -> _MountAttributes:
    logging.info(f"Searching {mount_point=} in /etc/mtab.")
    # For a mount point, this denotes the longest path that was seen in /etc/mtab.
    # This is therefore the point where that directory is mounted.
    longest_match_to_mount_point = ""
    # Find the longest match for the mount point.
    # I.e. consider line for "/parent/nested" over line for "/parent" alone.
    matched_line: str = ""
    for this_line in _mounts():
        this_tokens = _parse_mount_line(this_line)
        if this_tokens.fs == "autofs":
            # For autofs, another entry should exist which as "btrfs".
            # See also #54.
            continue
        if mount_point.startswith(this_tokens.mtab_mount_pt):
            if len(this_tokens.mtab_mount_pt) > len(longest_match_to_mount_point):
                longest_match_to_mount_point = this_tokens.mtab_mount_pt
                matched_line = this_line

    if not matched_line:
        raise ValueError(f"Mount point not found: {mount_point}")
    logging.info(f"Found matching mount line: {matched_line!r}")
    tokens = _parse_mount_line(matched_line)
    logging.info(f"Parsed into {tokens=}")

    if tokens.fs != "btrfs":
        raise ValueError(
            f"Mount point is not btrfs: {mount_point} ({tokens.fs})."
            "\nNOTE: If you are using recovery environment such as grub-btrfs, mount points are not auto detected."
            " You can use --subvol-map arg to pass the mount point to subvolume name mapping."
        )

    subvol_name = _get_mtab_param(key="subvol", all_params=tokens.params)
    subvol_id = int(_get_mtab_param(key="subvolid", all_params=tokens.params))
    logging.info(f"{subvol_name=}, {subvol_id=}")

    if tokens.mtab_mount_pt != mount_point:
        # The mount point was mounted automatically as a nested volume.
        #
        # Example 1: For mtab line -
        # '/dev/mapper/opened_rootbtrfs on /mnt/rootbtrfs type btrfs (rw,noatime,ssd,discard=async,space_cache=v2,subvolid=5,subvol=/)'
        # subvol_name="/"
        # mount_point="/mnt/rootbtrfs/@nestedvol"
        # tokens.mtab_mount_pt="/mnt/rootbtrfs".
        # REVISED subvol_name="/@nestedvol"
        #
        # Example 2: For mtab line -
        # '/dev/vda2 on / type btrfs (rw,relatime,discard=async,space_cache=v2,subvolid=258,subvol=/@)'
        # subvol_name="/@"
        # mount_point="/testnested"
        # tokens.mtab_mount_pt="/"
        # REVISED subvol_name="/@/testnested"
        #
        nested_part = mount_point.removeprefix(tokens.mtab_mount_pt)
        subvol_name = os.path.join(subvol_name, nested_part)
    return _MountAttributes(
        device=tokens.device, subvol_name=subvol_name, subvol_id=subvol_id
    )
