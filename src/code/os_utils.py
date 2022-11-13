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


def execute_sh(command: str, error_ok: bool = False) -> None:
  logging.info(f'Running {command}')
  try:
    subprocess.run(command.split(' '), check=True)
  except subprocess.CalledProcessError as e:
    if not error_ok:
      raise e
    logging.warning(f'Process had error {e}')


def last_pacman_command() -> str:
  logfile = '/var/log/pacman.log'
  matcher = re.compile(r'\[[\d\-:T+]*\] \[PACMAN\] Running \'(?P<cmd>.*)\'')
  with open(logfile) as f:
    for line in reversed(f.readlines()):
      match = matcher.match(line)
      if match:
        return match.group('cmd')
  raise ValueError('Last pacman command not found')


def timer_enabled() -> bool:
  return os.system('systemctl is-active yabsnap.timer >/dev/null') == 0


def eprint(*args: Any, **kwargs: Any) -> None:
  """Notifications meant for user, but not for redirection to any file."""
  print(*args, file=sys.stderr, **kwargs)
