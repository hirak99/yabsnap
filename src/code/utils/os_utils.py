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

from typing import Any, NoReturn


class CommandError(Exception):
    """Raised when a command is unsuccesful."""


def fatal_error(msg: str) -> NoReturn:
    """Shows a fatal error and exits.

    This produces a cleaner than raising an error. However, this also hides any
    backtrace that can be useful for debugging. Use it where it is easy to
    determine exactly what went wrong beyond any doubt from the message, both
    for a developer and the user.
    """
    logging.error(msg)
    sys.exit(-1)


def runsh_or_error(command: str) -> str:
    """Runs a shell command.

    Args:
      command: Command to run, e.g. "pacman-conf LogFile".

    Returns:
      Output of command.
    """
    logging.info(f"Running {command}")
    try:
        return subprocess.check_output(command.split(" ")).decode()
    except subprocess.CalledProcessError:
        # Exit context so this exception is not raised.
        pass
    # If we are here, the command could not be run.
    error_msg = f"Error running shell command: '{command}'"
    raise CommandError(error_msg)


def runsh(command: str) -> str | None:
    try:
        return runsh_or_error(command)
    except CommandError as exc:
        logging.warning(exc)
        return None


def command_exists(command: str) -> bool:
    """E.g. command_exists('rsync')"""
    return runsh(f"which {command}") is not None


def run_user_script(script_name: str, args: list[str]) -> bool:
    try:
        subprocess.check_call([script_name] + args)
    except FileNotFoundError:
        logging.warning(f"User script {script_name=} does not exist.")
        return False
    except subprocess.CalledProcessError:
        logging.warning(f"User script {script_name=} with {args=} resulted in error.")
        return False
    return True


def _get_pacman_log_path() -> str:
    logfile = runsh("pacman-conf LogFile")
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
    user_choice = input(f"{msg} [y/N] ")
    match user_choice.lower():
        case "y" | "yes":
            return True
        case _:
            eprint("Aborted.")
            return False


def is_sudo() -> bool:
    return os.getuid() == 0
