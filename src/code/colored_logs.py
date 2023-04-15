import logging
import os
import platform
import sys
from typing import TextIO


# Based on https://stackoverflow.com/q/7445658/196462, https://gist.github.com/ssbarnea/1316877
def _is_ansi_color_supported(handle: TextIO) -> bool:
    if (hasattr(handle, "isatty") and handle.isatty()) or (
        "TERM" in os.environ and os.environ["TERM"] == "ANSI"
    ):
        if platform.system() == "Windows" and not (
            "TERM" in os.environ and os.environ["TERM"] == "ANSI"
        ):
            # Windows console, no ANSI support.
            return False
        else:
            return True
    return False


# Based on https://stackoverflow.com/a/56944256/196462
class _CustomFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # grey = "\x1b[38;20m"
        grey = "\x1b[38;5;240m"
        yellow = "\x1b[33;20m"
        red = "\x1b[31;20m"
        bold_red = "\x1b[31;1m"
        reset = "\x1b[0m"

        level_colors = {
            logging.DEBUG: grey,
            logging.INFO: grey,
            logging.WARNING: yellow,
            logging.ERROR: red,
            logging.CRITICAL: bold_red,
        }

        log_format = (
            # "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
            "%(asctime)s %(levelname)s: %(message)s"
        )

        if _is_ansi_color_supported(sys.stderr):
            self._level_formats = {
                level: color + log_format + reset
                for level, color in level_colors.items()
            }
        else:
            self._level_formats = {level: log_format for level in level_colors}

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self._level_formats.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def setup_logging(level: int):
    logger = logging.getLogger()
    logger.setLevel(level)

    # Create console handler with a higher log level.
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    ch.setFormatter(_CustomFormatter())

    logger.addHandler(ch)
