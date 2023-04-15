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
import datetime
import logging

from . import colored_logs
from . import configs
from . import global_flags
from . import rollbacker
from . import os_utils
from . import snap_operator

from typing import Iterable


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="yabsnap")
    parser.add_argument(
        "--sync",
        help="Wait for btrfs to sync for any delete operations.",
        action="store_true",
    )
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
    subparsers.add_parser("list")
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


def _btrfs_sync(mount_paths: set[str]) -> None:
    for mount_path in sorted(mount_paths):
        if global_flags.FLAGS.dryrun:
            os_utils.eprint(f"Would sync {mount_path}")
            continue
        os_utils.eprint("Syncing ...", flush=True)
        os_utils.execute_sh(f"btrfs subvolume sync {mount_path}")


def _delete_snap(configs_iter: Iterable[configs.Config], path_suffix: str, sync: bool):
    mount_paths: set[str] = set()
    for config in configs_iter:
        snap = snap_operator.find_target(config, path_suffix)
        if snap:
            snap.delete()
            mount_paths.add(config.mount_path)

    if sync:
        _btrfs_sync(mount_paths)

    if not mount_paths:
        os_utils.eprint(f"Target {path_suffix} not found in any config.")


def _config_operation(command: str, source: str, comment: str, sync: bool):
    # Single timestamp for all operations.
    now = datetime.datetime.now()

    # Which mount paths to sync.
    mount_paths_to_sync: set[str] = set()

    # Commands that need to access existing config.
    for config in configs.iterate_configs(source=source):
        snapper = snap_operator.SnapOperator(config, now)
        if command == "internal-cronrun":
            snapper.scheduled()
        elif command == "internal-preupdate":
            snapper.on_pacman()
        elif command == "list":
            snapper.list_backups()
        elif command == "create":
            snapper.create(comment)
        else:
            raise ValueError(f"Command not implemented: {command}")

        if snapper.need_sync:
            mount_paths_to_sync.add(config.mount_path)

    if sync:
        _btrfs_sync(mount_paths_to_sync)


def main():
    args = _parse_args()
    command: str = args.command
    if not command:
        os_utils.eprint("Start with --help to see common args.")
        return

    if args.dry_run:
        global_flags.FLAGS.dryrun = True

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
            command=args.command, source=args.source, comment=comment, sync=args.sync
        )


if __name__ == "__main__":
    main()
