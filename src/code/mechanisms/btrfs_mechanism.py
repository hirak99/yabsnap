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

import logging

from . import abstract_mechanism
from . import rollback_btrfs
from .. import global_flags
from ..snapshot_logic import snap_metadata
from ..utils import os_utils
from ..utils import mtab_parser

from typing import override


def _execute_sh(cmd: str):
    if global_flags.FLAGS.dryrun:
        os_utils.eprint("Would run " + cmd)
    else:
        os_utils.runsh_or_error(cmd)


class BtrfsSnapMechanism(abstract_mechanism.SnapMechanism):
    @override
    def verify_volume(self, source: str) -> bool:
        # Based on https://stackoverflow.com/a/32865333/196462
        fstype = os_utils.runsh("stat -f --format=%T " + source)
        if not fstype:
            logging.warning(f"Not btrfs (cannot determine filesystem): {source}")
            return False
        if fstype.strip() != "btrfs":
            logging.warning(f"Not btrfs (filesystem not btrfs): {source}")
            return False
        inodenum = os_utils.runsh("stat --format=%i " + source)
        if not inodenum:
            logging.warning(f"Not btrfs (cannot determine inode): {source}")
            return False
        if inodenum.strip() != "256":
            logging.warning(
                f"Not btrfs (inode not 256, possibly a subdirectory of a btrfs mount): {source}"
            )
            return False
        return True

    @override
    def fill_metadata(self, metadata: snap_metadata.SnapMetadata) -> None:
        source = metadata.source
        mtab = mtab_parser.mount_attributes(source)
        # metadata.aux["source_subvol"] = mtab.subvol_name
        metadata.btrfs = snap_metadata.Btrfs(source_subvol=mtab.subvol_name)

    @override
    def create(self, source: str, destination: str):
        try:
            _execute_sh("btrfs subvolume snapshot -r " f"{source} {destination}")
        except os_utils.CommandError:
            logging.error("Unable to create; are you running as root?")
            raise

    @override
    def delete(self, destination: str):
        try:
            _execute_sh(f"btrfs subvolume delete {destination}")
        except os_utils.CommandError:
            logging.error("Unable to delete; are you running as root?")
            raise

    @override
    def rollback_gen(
        self,
        source_dests: list[tuple[snap_metadata.SnapMetadata, str]],
        live_subvol_map: dict[str, str] | None,
    ) -> list[str]:
        for metadata, _ in source_dests:
            source = metadata.source
            if live_subvol_map and source in live_subvol_map:
                logging.info(
                    f"Using mapped subvol for {source}. Skipping volume verification."
                )
                continue
            if not self.verify_volume(source):
                raise RuntimeError(
                    f"Mount point may no longer be a btrfs volume: {source!r}. "
                    " For certain recovery environments like grub-btrfs, volumes may not be correctly detected."
                    " You can use the `--live-subvol-map` arg to override auto detection."
                )
        return rollback_btrfs.rollback_gen(source_dests, live_subvol_map)

    @override
    def sync_paths(self, paths: set[str]):
        for mount_path in sorted(paths):
            if global_flags.FLAGS.dryrun:
                os_utils.eprint(f"Would sync {mount_path}")
                continue
            os_utils.eprint("Syncing ...", flush=True)
            os_utils.runsh_or_error(f"btrfs subvolume sync {mount_path}")
