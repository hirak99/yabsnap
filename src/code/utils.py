import logging
import re
import subprocess


def execute_sh(command: str, error_ok: bool = False) -> None:
  logging.info(f'Running {command}')
  try:
    subprocess.run(command.split(' '), check=True)
  except subprocess.CalledProcessError as e:
    if not error_ok:
      raise e
    logging.warn(f'Process had error {e}')


def last_pacman_command() -> str:
  logfile = '/var/log/pacman.log'
  matcher = re.compile(r'\[[\d\-:T+]*\] \[PACMAN\] Running \'(?P<cmd>.*)\'')
  with open(logfile) as f:
    for line in reversed(f.readlines()):
      match = matcher.match(line)
      if match:
        return match.group('cmd')
  raise ValueError('Last pacman command not found')
