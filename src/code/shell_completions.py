import logging
import os
import sys

from . import arg_parser
from . import configs
from .autocomplete import completions
from .snapshot_logic import snap_operator

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
    iszsh = "zsh" in os.environ.get("SHELL", "").lower()

    parser = arg_parser.make_parser()
    result = completions.get_completions(
        parser,
        sys.argv[2:],
        positional_arg_values=_positional_args,
        iszsh=iszsh,
        ignore_args=_IGNORE_ARGS,
    )
    print(result)


# To debug, run with the first parameter as anything but "yabsnap". E.g. -
# python -m code.shell_completions debug rollback-gen "--"
if __name__ == "__main__":
    if sys.argv[1] != "yabsnap":
        # Assume this is a direct run for debugging.
        logging.basicConfig(level=logging.DEBUG)
    logging.debug(sys.argv)
    main()
