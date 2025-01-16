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
from typing import Any


class CommandError(Exception):
    """Raised when a command is unsuccesful."""


def execute_sh(command: str, error_ok: bool = False) -> str | None:
    """Runs a shell command.

    Args:
      command: Command to run, e.g. "pacman-conf LogFile".
      error_ok: If True, returns None on error.
    """
    logging.info(f"Running {command}")
    try:
        return subprocess.check_output(command.split(" ")).decode()
    except subprocess.CalledProcessError as e:
        if not error_ok:
            raise CommandError(f"Unable to run command: {command}") from e
        logging.warning(f"Error running command: {e}")
        return None


def run_user_script(script_name: str, args: list[str]) -> bool:
    try:
        subprocess.check_call([script_name] + args)
    except FileNotFoundError:
        logging.warning(f"User script {script_name=} does not exist.")
        return False
    except subprocess.CalledProcessError:
        logging.warning(
            f"User script {script_name=} with {args=} resulted in error."
        )
        return False
    return True


def _get_pacman_log_path() -> str:
    logfile = execute_sh("pacman-conf LogFile", error_ok=True)
    if logfile is None:
        logging.warning("Unable to determine pacman log path. Using default.")
        return "/var/log/pacman.log"
    return logfile.strip()


def last_pacman_command() -> str:
    logfile = _get_pacman_log_path()
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


def interactive_confirm(msg: str) -> bool:
    user_choice = input(msg)
    match user_choice:
        case "y" | "Y" | "yes" | "Yes" | "YES":
            return True
        case _:
            print("Aborted.")
            return False
