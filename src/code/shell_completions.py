import logging
import sys

from . import arg_parser
from .autocomplete import completions

_IGNORE_ARGS = {"internal-cronrun", "internal-preupdate"}


def _positional_args(name: str) -> list[str]:
    logging.debug(f"Positional args for '{name}'")
    return []


def main():
    parser = arg_parser.make_parser()
    results = completions.get_completions(
        parser, sys.argv[2:], positional_arg_values=_positional_args
    )
    print(" ".join(x for x in results if x not in _IGNORE_ARGS))


# To debug, run with the first parameter as anything but "yabsnap". E.g. -
# python -m code.shell_completions debug rollback-gen "--"
if __name__ == "__main__":
    if sys.argv[1] != "yabsnap":
        # Assume this is a direct run for debugging.
        logging.basicConfig(level=logging.DEBUG)
    logging.debug(sys.argv)
    main()
