import logging
import subprocess


def execute_sh(command: str, error_ok: bool = False) -> None:
  logging.info(f'Running {command}')
  try:
    subprocess.run(command.split(' '), check=True)
  except subprocess.CalledProcessError as e:
    if not error_ok:
      raise e
    logging.warn(f'Process had error {e}')
