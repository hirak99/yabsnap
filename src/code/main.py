# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import collections
import datetime
import itertools
import logging
import shlex

from . import configs
from . import global_flags
from .mechanisms import snap_type_enum
from .mechanisms import snap_mechanisms
from .snapshot_logic import batch_deleter
from .snapshot_logic import rollbacker
from .snapshot_logic import snap_operator
from .utils import colored_logs
from .utils import os_utils

from typing import Iterable


def _parse_live_subvol_map(map_str: str) -> dict[str, str]:
    """Helper to parse the --live-subvol-map argument.

    Example: --live-subvol-map "/:@ /home:@home"
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


def _parse_args() -> argparse.Namespace:
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
            "--live-subvol-map",
            type=_parse_live_subvol_map,
            required=False,
            help="Mapping of source path to live subvolume name. "
            "Specify this if the system is in a recovery mode and subvolume names are not auto-detected. "
            'Example: --live-subvol-map "/:@"'
            "Use space to delimit multiple mappings if multiple subvolumes are rolled back. "
            'Example: --live-subvol-map "/:@ /home:@home"',
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

    args = parser.parse_args()
    return args


def _sync(configs_to_sync: list[configs.Config]):
    paths_to_sync: dict[snap_type_enum.SnapType, set[str]] = collections.defaultdict(
        set
    )
    for config in configs_to_sync:
        paths_to_sync[config.snap_type].add(config.mount_path)
    for snap_type, paths in sorted(paths_to_sync.items()):
        snap_mechanisms.get(snap_type).sync_paths(paths)


def _set_ttl(configs_iter: Iterable[configs.Config], path_suffix: str, ttl_str: str):
    for config in configs_iter:
        snap = snap_operator.find_target(config, path_suffix)
        if snap:
            snap.set_ttl(ttl_str, now=datetime.datetime.now())


def _delete_snap(configs_iter: Iterable[configs.Config], path_suffix: str, sync: bool):
    to_sync: list[configs.Config] = []
    for config in configs_iter:
        snap = snap_operator.find_target(config, path_suffix)
        if snap:
            snap.delete()
            to_sync.append(config)

        config.call_post_hooks()

    if sync:
        _sync(to_sync)


def _batch_delete_snaps(
    configs_iter: Iterable[configs.Config],
    args: argparse.Namespace,
    sync: bool,
):
    config_snaps_mapping_tuple = list(
        batch_deleter.create_config_snapshots_mapping(configs_iter)
    )
    args_as_dict = vars(args)
    filters = batch_deleter.get_filters(args_as_dict)

    targets = list(
        batch_deleter.apply_snapshot_filters(config_snaps_mapping_tuple, *filters)
    )
    if sum(len(mapping.snaps) for mapping in targets) == 0:
        os_utils.eprint("No snapshots matching the criteria were found.")
        return

    batch_deleter.show_snapshots_to_be_deleted(targets)

    if os_utils.interactive_confirm(
        "Are you sure you want to delete the above snapshots?"
    ):
        snaps = itertools.chain.from_iterable(mapping.snaps for mapping in targets)
        batch_deleter.delete_snapshots(snaps)

    if sync:
        to_sync = batch_deleter.get_to_sync_list(mapping.config for mapping in targets)
        _sync(to_sync)


def _config_operation(
    command: str, source: str | None, comment: str | None, sync: bool
):
    # Single timestamp for all operations.
    now = datetime.datetime.now()

    # Which mount paths to sync.
    to_sync: list[configs.Config] = []

    # Commands that need to access existing config.
    for config in configs.iterate_configs(source=source):
        snapper = snap_operator.SnapOperator(config, now)
        if command == "internal-cronrun":
            snapper.scheduled()
        elif command == "internal-preupdate":
            snapper.on_pacman()
        elif command == "list":
            snapper.list_snaps()
        elif command == "list-json":
            snapper.list_snaps_json()
        elif command == "create":
            snapper.create(comment)
        else:
            raise ValueError(f"Command not implemented: {command}")

        if snapper.snaps_deleted:
            if config.snap_type == snap_type_enum.SnapType.BTRFS:
                to_sync.append(config)
        if snapper.snaps_created or snapper.snaps_deleted:
            config.call_post_hooks()

    if sync:
        _sync(to_sync)


def main():
    args = _parse_args()
    command: str = args.command
    if not command:
        os_utils.eprint("Start with --help to see common args.")
        return

    if args.dry_run:
        global_flags.FLAGS.dryrun = True
    configs.USER_CONFIG_FILE = args.config_file

    colored_logs.setup_logging(level=logging.INFO if args.verbose else logging.WARNING)

    if command == "create-config":
        configs.create_config(args.config_name, args.source)
    elif command == "delete":
        _delete_snap(
            configs.iterate_configs(source=args.source),
            path_suffix=args.target_suffix,
            sync=args.sync,
        )
    elif command == "set-ttl":
        _set_ttl(
            configs.iterate_configs(source=args.source),
            path_suffix=args.target_suffix,
            ttl_str=args.ttl,
        )
    elif command == "batch-delete":
        _batch_delete_snaps(
            configs.iterate_configs(source=args.source),
            args=args,
            sync=args.sync,
        )
    elif command == "rollback":
        rollbacker.rollback(
            configs.iterate_configs(source=args.source),
            args.target_suffix,
            live_subvol_map=args.live_subvol_map,
            execute=True,
            no_confirm=args.noconfirm,
        )
    elif command == "rollback-gen":
        rollbacker.rollback(
            configs.iterate_configs(source=args.source),
            args.target_suffix,
            live_subvol_map=args.live_subvol_map,
            execute=args.execute,
        )
        # Does `rollback-gen` subcommand require the optional parameter `--nocofirm` ?
    else:
        comment = getattr(args, "comment", "")
        _config_operation(
            command=args.command,
            source=args.source,
            comment=comment,
            sync=args.sync,
        )

    if configs.is_schedule_enabled() and not os_utils.timer_enabled():
        os_utils.eprint(
            "\n".join(
                [
                    "",
                    "*** NOTE - Backup schedule exists but yabsnap.timer is not active ***",
                    "To enable scheduled backups, please run -",
                    "  sudo systemctl enable --now yabsnap.timer",
                    "",
                ]
            )
        )


if __name__ == "__main__":
    main()
