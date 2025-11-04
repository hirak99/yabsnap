import logging
import sys

from . import arg_parser
from .autocomplete import completions

_IGNORE_ARGS = {"internal-cronrun", "internal-preupdate"}


def main():
    parser = arg_parser.make_parser()
    completer = completions.Completer()
    results = completer.get_completions(parser, sys.argv[5:])
    print(" ".join(x for x in results if x not in _IGNORE_ARGS))


if __name__ == "__main__":
    # logging.basicConfig(level=logging.DEBUG)
    logging.debug(sys.argv)
    main()
