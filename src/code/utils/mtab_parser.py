import dataclasses
import functools
import json
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
class _MountEntry:
    device: str
    mtab_mount_pt: str
    fs: str
    params: str


@functools.cache
def _findmnt() -> dict[str, list[dict[str, str]]]:
    output = os_utils.runsh_or_error("findmnt --mtab -J")
    return json.loads(output)


def _mount_entries() -> list[_MountEntry]:
    mounts_json = _findmnt()

    def remove_square_brackets(s: str) -> str:
        # Some sources look like "/dev/mapper/luksdev[/@]".
        if s.endswith("]"):
            # Find the first "[" from end and take string before that.
            return s[: s.rfind("[")]
        return s

    result: list[_MountEntry] = []
    for x in mounts_json["filesystems"]:
        result.append(
            _MountEntry(
                device=remove_square_brackets(x["source"]),
                mtab_mount_pt=x["target"],
                fs=x["fstype"],
                params=x["options"],
            )
        )
    return result


@functools.cache
def mount_attributes(mount_point: str) -> _MountAttributes:
    logging.info(f"Searching {mount_point=} in /etc/mtab.")
    # For a mount point, this denotes the longest path that was seen in /etc/mtab.
    # This is therefore the point where that directory is mounted.
    longest_match_to_mount_point = ""
    # Find the longest match for the mount point.
    # I.e. consider line for "/parent/nested" over line for "/parent" alone.
    matched_line: _MountEntry | None = None
    for this_tokens in _mount_entries():
        logging.info(this_tokens)
        if this_tokens.fs == "autofs":
            # For autofs, another entry should exist which as "btrfs".
            # See also #54.
            continue
        if mount_point.startswith(this_tokens.mtab_mount_pt):
            if len(this_tokens.mtab_mount_pt) > len(longest_match_to_mount_point):
                longest_match_to_mount_point = this_tokens.mtab_mount_pt
                matched_line = this_tokens

    if matched_line is None:
        raise ValueError(f"Mount point not found: {mount_point}")
    logging.info(f"Found matching mount line: {matched_line!r}")

    if matched_line.fs != "btrfs":
        raise ValueError(
            f"Mount point is not btrfs: {mount_point} ({matched_line.fs})."
            "\nNOTE: If you are using recovery environment such as grub-btrfs, mount points are not auto detected."
            " You can use --subvol-map arg to pass the mount point to subvolume name mapping."
        )

    subvol_name = _get_mtab_param(key="subvol", all_params=matched_line.params)
    subvol_id = int(_get_mtab_param(key="subvolid", all_params=matched_line.params))
    logging.info(f"{subvol_name=}, {subvol_id=}")

    if matched_line.mtab_mount_pt != mount_point:
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
        nested_part = mount_point.removeprefix(matched_line.mtab_mount_pt)
        subvol_name = os.path.join(subvol_name, nested_part)
    return _MountAttributes(
        device=matched_line.device, subvol_name=subvol_name, subvol_id=subvol_id
    )
