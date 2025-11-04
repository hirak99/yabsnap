import argparse
import shlex

from .snapshot_logic import batch_deleter


def _parse_subvol_map(map_str: str) -> dict[str, str]:
    """Helper to parse the --subvol-map argument.

    Example: --subvol-map "/:@ /home:@home"
    will be parsed as {"/": "@", "/home": "home"}.
    """
    mapping: dict[str, str] = {}
    pairs = shlex.split(map_str)
    for pair in pairs:
        if ":" not in pair:
            raise ValueError(f"Invalid mapping pair (missing ':'): {pair}")
        live_path, subvol_name = pair.split(":", 1)
        mapping[live_path] = subvol_name
    return mapping


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="yabsnap")
    parser.add_argument(
        "--sync",
        help="Wait for btrfs to sync for any delete operations.",
        action="store_true",
    )
    parser.add_argument("--config-file", help="Specify a config file to use.")
    parser.add_argument("--source", help="Restrict to config with this source path.")
    parser.add_argument(
        "--dry-run",
        help="If passed, will disable all snapshot creation and deletion.",
        action="store_true",
    )
    parser.add_argument(
        "--verbose", help="Sets log-level to INFO.", action="store_true"
    )

    # title - Shows as [title]: before commands are listed.
    # metavar - The string is printed below the title. If None, all commands including hidden ones are printed.
    subparsers = parser.add_subparsers(dest="command", title="command", metavar="")

    # A message to be added to help for all commands that honor --source or --config-file.
    source_message = " Optionally use with --source or --config-file."

    # Creates a new config by NAME.
    create_config = subparsers.add_parser(
        "create-config", help="Bootstrap a config for new filesystem to snapshot."
    )
    create_config.add_argument(
        "config_name", help='Name to be given to config file, e.g. "home".'
    )

    # User commands.
    subparsers.add_parser("list", help="List all managed snaps." + source_message)
    subparsers.add_parser(
        "list-json", help="Machine readable list of all managed snaps." + source_message
    )

    # Creates an user snapshot.
    create = subparsers.add_parser(
        "create", help="Create new snapshots." + source_message
    )
    create.add_argument("--comment", help="Comment attached to this snapshot.")

    # Set TTL for a snapshot.
    set_ttl = subparsers.add_parser(
        "set-ttl", help="Set a TTL for matching snapshots." + source_message
    )
    set_ttl.add_argument(
        "--ttl",
        type=str,
        required=True,
        help="Time to live from now, for instance '1 day' or '20 years'. Empty '' will delete the ttl. If ttl is present, it will take precedence over any other automated management.",
    )

    # Delete a snapshot.
    delete = subparsers.add_parser(
        "delete", help="Delete matching snapshots." + source_message
    )

    # Batch delete snapshots.
    batch_delete = subparsers.add_parser(
        "batch-delete",
        help="Batch delete snapshots created by yabsnap." + source_message,
    )
    batch_delete.add_argument(
        "--indicator",
        type=str,
        choices=("S", "I", "U"),
        default=None,
        help="Filter out snapshots that have a specific indicator identifier.",
    )
    batch_delete.add_argument(
        "--start",
        type=batch_deleter.iso8601_to_timestamp_string,
        default=None,
        help="Where to start deleting snapshots. Timestamp can be 'YYYY-MM-DD HH:MM[:SS]'",
    )
    batch_delete.add_argument(
        "--end",
        type=batch_deleter.iso8601_to_timestamp_string,
        default=None,
        help="Where to stop deleting snapshots. Timestamp can be 'YYYY-MM-DD HH:MM[:SS]'",
    )

    # Generates a script for rolling back.
    rollback_gen = subparsers.add_parser(
        "rollback-gen",
        help="Generate script to rollback one or more snaps." + source_message,
    )
    rollback_gen.add_argument(
        "--execute",
        action="store_true",
        help="Generate rollback script and execute.",
    )

    rollback = subparsers.add_parser(
        "rollback",
        help="Generate rollback script and run. Equivalent to `rollback-gen --execute`",
    )
    rollback.add_argument(
        "--noconfirm",
        action="store_true",
        help="Execute the rollback script without confirmation.",
    )

    for rollback_command in [rollback_gen, rollback]:
        # NOTE from https://github.com/hirak99/yabsnap/discussions/66 -
        # > The original rollback-gen command did not function correctly within a
        # > read-only snapshot environment (e.g., a recovery environment booted by
        # > grub-btrfs). This was because it relies on auto-detection to find the
        # > currently mounted subvolume names. In a read-only snapshot, the system
        # > incorrectly reports the mountpoint as the snapshot itself (e.g.,
        # > /@.snapshots/snap...) or an overlay, preventing the generation of a
        # > correct rollback script.
        rollback_command.add_argument(
            "--subvol-map",
            type=_parse_subvol_map,
            required=False,
            help="Mapping of source path to live subvolume name. "
            "Specify this if the system is in a recovery mode and subvolume names are not auto-detected. "
            'Example: --subvol-map "/:@"'
            "Use space to delimit multiple mappings if multiple subvolumes are rolled back. "
            'Example: --subvol-map "/:@ /home:@home"',
        )

    for command_with_target in [
        delete,
        rollback_gen,
        rollback,
        set_ttl,
    ]:
        command_with_target.add_argument(
            "target_suffix",
            help="Datetime string, or full path of a snapshot." + source_message,
        )

    # Internal commands used in scheduling and pacman hook.
    # Not having a help= makes them unlisted in --help.
    subparsers.add_parser("internal-cronrun")
    subparsers.add_parser("internal-preupdate")

    return parser
