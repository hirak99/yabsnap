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
import logging
from typing import Iterable

from . import colored_logs
from . import configs
from . import global_flags
from . import os_utils
from . import rollbacker
from . import snap_operator
from .mechanisms import snap_mechanisms


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
    subparsers = parser.add_subparsers(dest="command")

    # User commands.
    subparsers.add_parser("list", help="List all managed snaps.")
    subparsers.add_parser(
        "list-json", help="Machine readable list of all managed snaps."
    )
    create = subparsers.add_parser("create", help="Create new snapshots.")
    create.add_argument("--comment", help="Comment attached to this snapshot.")
    create_config = subparsers.add_parser(
        "create-config", help="Bootstrap a config for new filesystem to snapshot."
    )
    create_config.add_argument(
        "config_name", help='Name to be given to config file, e.g. "home".'
    )
    delete = subparsers.add_parser(
        "delete", help="Delete a snapshot created by yabsnap."
    )
    rollback = subparsers.add_parser(
        "rollback-gen", help="Generate script to rollback one or more snaps."
    )

    for command_with_target in [delete, rollback]:
        command_with_target.add_argument(
            "target_suffix", help="Datetime string, or full path of a snapshot."
        )

    # Internal commands used in scheduling and pacman hook.
    subparsers.add_parser("internal-cronrun", help=argparse.SUPPRESS)
    subparsers.add_parser("internal-preupdate", help=argparse.SUPPRESS)

    args = parser.parse_args()
    return args


def _sync(configs_to_sync: list[configs.Config]):
    paths_to_sync: dict[snap_mechanisms.SnapType, set[str]] = collections.defaultdict(
        set
    )
    for config in configs_to_sync:
        paths_to_sync[config.snap_type].add(config.mount_path)
    for snap_type, paths in sorted(paths_to_sync.items()):
        snap_mechanisms.get(snap_type).sync_paths(paths)


def _delete_snap(configs_iter: Iterable[configs.Config], path_suffix: str, sync: bool):
    to_sync: list[configs.Config] = []
    for config in configs_iter:
        snap = snap_operator.find_target(config, path_suffix)
        if snap:
            snap.delete()
            if config.snap_type == snap_mechanisms.SnapType.BTRFS:
                to_sync.append(config)

        config.call_post_hooks()

    if sync:
        _sync(to_sync)

    if not to_sync:
        os_utils.eprint(f"Target {path_suffix} not found in any config.")


def _config_operation(command: str, source: str, comment: str, sync: bool):
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
            if config.snap_type == snap_mechanisms.SnapType.BTRFS:
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

    if configs.is_schedule_enabled():
        if not os_utils.timer_enabled():
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

    if command == "create-config":
        configs.create_config(args.config_name, args.source)
    elif command == "delete":
        _delete_snap(
            configs.iterate_configs(source=args.source),
            path_suffix=args.target_suffix,
            sync=args.sync,
        )
    elif command == "rollback-gen":
        rollbacker.rollback(
            configs.iterate_configs(source=args.source), args.target_suffix
        )
    else:
        comment = getattr(args, "comment", "")
        _config_operation(
            command=args.command,
            source=args.source,
            comment=comment,
            sync=args.sync,
        )


if __name__ == "__main__":
    main()
