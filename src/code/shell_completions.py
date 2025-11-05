"""Yabsnap shell completions.

To test -
$ STYLE=zsh python -m src.code.shell_completions debug ""

Or, enable the flag during normal operations -
export YABSNAP_COMPLETION_DEBUG=True
$ yabsnap <TAB>

"""

import logging
import os
import sys

from . import arg_parser
from . import configs
from .autocomplete import completions
from .snapshot_logic import snap_operator

# If set to True, yabsnap completions will print debug output.
_DEBUG_ENV_FLAG = "YABSNAP_COMPLETION_DEBUG"

_IGNORE_ARGS = {"internal-cronrun", "internal-preupdate", "-h"}


def _positional_args(name: str) -> list[str]:
    logging.debug(f"Positional args for '{name}'")

    if name == "target_suffix":
        candidates: set[str] = set()

        for config in configs.iterate_configs(source=None):
            for snap in snap_operator.get_existing_snaps(config):
                candidates.add(os.path.basename(snap.target))
                target_suffix = snap.target.removeprefix(config.dest_prefix)
                candidates.add(target_suffix)
        return sorted(candidates)

    logging.debug(f"Positional arg candidates is not handled: '{name}'")
    return []


def main():
    parser = arg_parser.make_parser()
    result = completions.get_completions(
        parser,
        sys.argv[2:],
        positional_arg_values=_positional_args,
        ignore_args=_IGNORE_ARGS,
    )
    print(result)


if __name__ == "__main__":
    if sys.argv[1] != "yabsnap" or os.getenv(_DEBUG_ENV_FLAG, "").lower() == "true":
        # Assume this is a direct run for debugging.
        logging.basicConfig(level=logging.DEBUG)
    logging.debug(sys.argv)
    main()
