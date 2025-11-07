"""Sets up ArgumentParser for yabsnap.

This is also used for shell completion.
This should be kept free of yabsnap-specific code.
"""

import argparse
import shlex


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
        help="Wait for filesystem to sync after deleting snapshots.",
        action="store_true",
    )
    parser.add_argument("--config-file", help="Path to the config file to use.")
    parser.add_argument(
        "--source", help="Only use config with matching `source` value."
    )
    parser.add_argument(
        "--dry-run",
        help="Disable all snapshot creation and deletion (dry run mode).",
        action="store_true",
    )
    parser.add_argument("--verbose", help="Set log level to INFO.", action="store_true")

    # title - Shows as [title]: before commands are listed.
    # metavar - The string is printed below the title. If None, all commands including hidden ones are printed.
    subparsers = parser.add_subparsers(dest="command", title="command", metavar="")

    # A message to be added to help for all commands that honor --source or --config-file.
    source_message = " Supports --source or --config-file."

    # Creates a new config by NAME.
    create_config = subparsers.add_parser(
        "create-config", help="Create a config for a new filesystem to snapshot."
    )
    create_config.add_argument(
        "config_name", help='Name for the config file (e.g., "home").'
    )

    # User commands.
    subparsers.add_parser("list", help="List all managed snapshots." + source_message)
    subparsers.add_parser(
        "list-json",
        help="List all managed snapshots in JSON Lines format." + source_message,
    )

    # Creates an user snapshot.
    create = subparsers.add_parser(
        "create", help="Create new snapshots." + source_message
    )
    create.add_argument("--comment", help="Attach a comment to the snapshot.")

    # Set TTL for a snapshot.
    set_ttl = subparsers.add_parser(
        "set-ttl",
        help="Set a TTL (time to live) for matching snapshots." + source_message,
    )
    set_ttl.add_argument(
        "--ttl",
        type=str,
        required=True,
        help="Time to live (e.g., '1 day', '20 years'). Use '' (empty) to remove TTL. If set, TTL overrides other automated management.",
    )

    # Delete a snapshot.
    delete = subparsers.add_parser(
        "delete", help="Delete matching snapshot(s)." + source_message
    )

    # Batch delete snapshots.
    batch_delete = subparsers.add_parser(
        "batch-delete",
        help="Delete multiple snapshots." + source_message,
    )
    batch_delete.add_argument(
        "--indicator",
        type=str,
        choices=("S", "I", "U"),
        default=None,
        help="Only delete snapshots with the specified indicator (S, I, or U).",
    )
    batch_delete.add_argument(
        "--start",
        type=str,
        default=None,
        help="Start deleting from this timestamp ('YYYY-MM-DD HH:MM[:SS]').",
    )
    batch_delete.add_argument(
        "--end",
        type=str,
        default=None,
        help="Stop deleting at this timestamp ('YYYY-MM-DD HH:MM[:SS]').",
    )

    # Generates a script for rolling back.
    rollback_gen = subparsers.add_parser(
        "rollback-gen",
        help="Generate a script to rollback one or more snapshots." + source_message,
    )
    rollback_gen.add_argument(
        "--execute",
        action="store_true",
        help="Immediately execute the generated rollback script.",
    )

    rollback = subparsers.add_parser(
        "rollback",
        help="Generate and run a rollback script (same as `rollback-gen --execute`).",
    )
    rollback.add_argument(
        "--noconfirm",
        action="store_true",
        help="Run rollback without asking for confirmation.",
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
            help="Map source paths to live subvolume names (for recovery mode when auto-detection fails). "
            'Example: --subvol-map "/:@" /home:@home"',
        )

    for command_with_target in [
        delete,
        rollback_gen,
        rollback,
        set_ttl,
    ]:
        command_with_target.add_argument(
            "target_suffix",
            help="Datetime string or full path of the snapshot to target."
            + source_message,
        )

    # Internal commands used in scheduling and pacman hook.
    # Not having a help= makes them unlisted in --help.
    subparsers.add_parser("internal-cronrun")
    subparsers.add_parser("internal-preupdate")

    return parser
