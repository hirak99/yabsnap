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
import platform
import sys

from typing import TextIO


# Based on https://stackoverflow.com/q/7445658/196462, https://gist.github.com/ssbarnea/1316877
def _is_ansi_color_supported(textout: TextIO) -> bool:
    if (hasattr(textout, "isatty") and textout.isatty()) or (
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

        common_fmt = "%(levelname)s: [%(filename)s:%(lineno)d] %(message)s"
        self._level_formats = {
            logging.DEBUG: common_fmt,
            logging.INFO: common_fmt,
            logging.WARNING: common_fmt,
            logging.ERROR: common_fmt,
            logging.CRITICAL: common_fmt,
        }

        if _is_ansi_color_supported(sys.stderr):
            self._level_formats = {
                level: color + self._level_formats[level] + reset
                for level, color in level_colors.items()
            }

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
