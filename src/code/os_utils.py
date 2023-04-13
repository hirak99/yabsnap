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
import re
import subprocess
import sys

from typing import Any, Optional


def execute_sh(command: str, error_ok: bool = False) -> Optional[str]:
    logging.info(f"Running {command}")
    try:
        return subprocess.check_output(command.split(" ")).decode()
    except subprocess.CalledProcessError as e:
        if not error_ok:
            raise e
        logging.warning(f"Error running command: {e}")
        return None


def is_btrfs_volume(mount_point: str) -> bool:
    """Test if directory is a btrfs volume."""
    # Based on https://stackoverflow.com/a/32865333/196462
    fstype = execute_sh("stat -f --format=%T " + mount_point, error_ok=True)
    if not fstype:
        logging.warning(f"Not btrfs (cannot determine filesystem): {mount_point}")
        return False
    if fstype.strip() != "btrfs":
        logging.warning(f"Not btrfs (filesystem not btrfs): {mount_point}")
        return False
    inodenum = execute_sh("stat --format=%i " + mount_point, error_ok=True)
    if not inodenum:
        logging.warning(f"Not btrfs (cannot determine inode): {mount_point}")
        return False
    if inodenum.strip() != "256":
        logging.warning(
            f"Not btrfs (inode not 256, possibly a subdirectory of a btrfs mount): {mount_point}"
        )
        return False
    return True


def last_pacman_command() -> str:
    logfile = "/var/log/pacman.log"
    matcher = re.compile(r"\[[\d\-:T+]*\] \[PACMAN\] Running \'(?P<cmd>.*)\'")
    with open(logfile) as f:
        for line in reversed(f.readlines()):
            match = matcher.match(line)
            if match:
                return match.group("cmd")
    raise ValueError("Last pacman command not found")


def timer_enabled() -> bool:
    return os.system("systemctl is-active yabsnap.timer >/dev/null") == 0


def eprint(*args: Any, **kwargs: Any) -> None:
    """Notifications meant for user, but not for redirection to any file."""
    print(*args, file=sys.stderr, **kwargs)
