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

from . import arg_parser
from . import configs
from . import global_flags
from .mechanisms import snap_mechanisms
from .mechanisms import snap_type_enum
from .snapshot_logic import batch_deleter
from .snapshot_logic import rollbacker
from .snapshot_logic import snap_operator
from .utils import colored_logs
from .utils import os_utils

from typing import Iterable


def _parse_args() -> argparse.Namespace:
    parser = arg_parser.make_parser()
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
            subvol_map=args.subvol_map,
            execute=True,
            no_confirm=args.noconfirm,
        )
    elif command == "rollback-gen":
        rollbacker.rollback(
            configs.iterate_configs(source=args.source),
            args.target_suffix,
            subvol_map=args.subvol_map,
            execute=args.execute,
        )
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
