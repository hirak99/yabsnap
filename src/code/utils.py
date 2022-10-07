import dataclasses
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


@dataclasses.dataclass
class MountAttributes:
  device: str
  subvol_name: str


def get_mount_attributes(mount_point: str) -> MountAttributes:
  for line in open('/etc/mtab'):
    tokens = line.split()
    if tokens[1] == mount_point:
      break
  else:
    raise ValueError(f'Mount point not found: {mount_point}')

  if tokens[2] != 'btrfs':
    raise ValueError(f'Mount point is not btrfs: {mount_point} ({tokens[2]})')
  for mount_param in tokens[3].split(','):
    subvol_prefix = 'subvol='
    if not mount_param.startswith(subvol_prefix):
      continue
    subvol_name = mount_param[len(subvol_prefix):]
    return MountAttributes(device=tokens[0], subvol_name=subvol_name)
  raise ValueError(f'Could not determine subvol in {line!r}')
