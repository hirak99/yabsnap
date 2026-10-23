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
import os

from .. import global_flags
from ..snapshot_logic import snap_metadata
from ..utils import mtab_parser
from ..utils import os_utils
from . import abstract_mechanism
from . import rollback_btrfs

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
        metadata.btrfs = snap_metadata.Btrfs(source_subvol=mtab.subvol_name)

    @override
    def create(self, source: str, destination: str):
        try:
            _execute_sh(f"btrfs subvolume snapshot -r {source} {destination}")
        except os_utils.CommandError as exc:
            raise RuntimeError("Unable to create; are you running as root?") from exc

    @override
    def delete(self, destination: str):
        try:
            _execute_sh(f"btrfs subvolume delete {destination}")
        except os_utils.CommandError as exc:
            raise RuntimeError("Unable to delete; are you running as root?") from exc

    @override
    def _nested_dest_reason(self, source: str, dest_prefix: str) -> str | None:
        destdir = os.path.dirname(dest_prefix.rstrip("/"))
        if not destdir:
            return None
        try:
            live = mtab_parser.mount_attributes(source)
            store = mtab_parser.mount_attributes(destdir)
        except (ValueError, RuntimeError) as exc:
            logging.debug(f"Skipping nested-dest check for {source!r}: {exc}")
            return None
        if store.device != live.device:
            return None
        live_sub = "/" + live.subvol_name.strip("/")
        store_sub = "/" + store.subvol_name.strip("/")
        if live_sub == "/":
            inside = True  # Source is the whole filesystem; same device means inside.
        else:
            inside = store_sub == live_sub or store_sub.startswith(live_sub + "/")
        if not inside:
            return None
        return (
            f"snapshot storage {destdir!r} (subvolume {store.subvol_name!r}) is inside "
            f"the source subvolume {live.subvol_name!r} for {source!r}; move `dest_prefix` "
            "to a separate subvolume (e.g. `dest_prefix = /.snapshots/@root-` with "
            "`/.snapshots` on its own subvolume)"
        )

    @override
    def rollback_gen(
        self,
        snapshots: list[abstract_mechanism.LightSnapshot],
        subvol_map: dict[str, str] | None,
    ) -> list[str]:
        for snap in snapshots:
            source = snap.metadata.source
            if subvol_map and source in subvol_map:
                logging.info(
                    f"Using mapped subvol for {source}. Skipping volume verification."
                )
                continue
            if not self.verify_volume(source):
                raise RuntimeError(
                    f"Mount point may no longer be a btrfs volume: {source!r}. "
                    " For certain recovery environments like grub-btrfs, volumes may not be correctly detected."
                    " You can use the `--subvol-map` arg to override auto detection."
                )
        return rollback_btrfs.rollback_gen(snapshots, subvol_map)

    @override
    def sync_paths(self, paths: set[str]):
        for mount_path in sorted(paths):
            if global_flags.FLAGS.dryrun:
                os_utils.eprint(f"Would sync {mount_path}")
                continue
            os_utils.eprint("Syncing ...", flush=True)
            os_utils.runsh_or_error(f"btrfs subvolume sync {mount_path}")
