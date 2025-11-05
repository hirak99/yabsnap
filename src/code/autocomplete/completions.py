"""General purpose auto-complete handler."""

# The following when run will enable completions. It can be placed into -
# # /usr/share/bash-completion/completions/myprog

# _myprog_completions() {
#     local cmd
#     cmd="${COMP_WORDS[0]}"  # The command name (myprog)
#
#     # Call the Python script for completion
#     # "${COMP_LINE}"  : Entire line including commant.
#     # "${COMP_POINT}" : Where the cursor is.
#     # "$COMP_CWORD"   : Current word.
#     # "${COMP_WORDS[@]}" : Multiple args, e.g. ['command', 'arg1', 'arg2', ...].
#     # sys.argv[1]: The command.
#     # sys.argv[2:]: List of all words following the command.
#     COMPREPLY=( $(python3 myprog_completions.py "${COMP_WORDS[@]}") )
#
#     return 0
# }
#
# complete -F _myprog_completions myprog


import argparse
import dataclasses
import enum
import functools
import logging

from typing import Callable


class _OptionType(enum.Enum):
    OPTION = 1
    SUBPARSER = 2
    POSITIONAL = 3


@dataclasses.dataclass(frozen=True)
class _Option:
    name: str
    help: str | None
    type: _OptionType
    # None iff type == SUBPARSER.
    nargs: int | None
    # Present iff type == SUBPARSER.
    subparser: argparse.ArgumentParser | None = None


@dataclasses.dataclass
class _ParserWrapper:
    """Convenience class to bookkeep parser related fields."""

    parser: argparse.ArgumentParser
    nargs_to_read: int = 0
    num_positionals_used: int = 0

    def __post_init__(self):
        self.valid_options = _get_parser_accepted_args(self.parser)
        self.positionals: list[str] = [
            x.name
            for x in self.valid_options.values()
            if x.type == _OptionType.POSITIONAL
        ]

    def filter_by_types(self, types: list[_OptionType]) -> list[str]:
        return [x.name for x in self.valid_options.values() if x.type in types]


@functools.cache
def _get_parser_accepted_args(parser: argparse.ArgumentParser) -> dict[str, _Option]:
    # Argument, and how many words to follow.
    cands: dict[str, _Option] = {}
    for action in parser._actions:
        match action:
            case (
                argparse._HelpAction() | argparse._StoreConstAction()  # pyright: ignore
            ):
                for x in action.option_strings:
                    cands[x] = _Option(
                        name=x, nargs=0, type=_OptionType.OPTION, help=action.help
                    )
            case argparse._StoreAction():  # pyright: ignore
                if action.option_strings:
                    for x in action.option_strings:
                        cands[x] = _Option(
                            name=x, nargs=1, type=_OptionType.OPTION, help=action.help
                        )
                else:
                    cands[action.dest] = _Option(
                        name=action.dest,
                        nargs=0,
                        type=_OptionType.POSITIONAL,
                        help=action.help,
                    )
            case argparse._SubParsersAction():  # pyright: ignore
                for k, v in action.choices.items():
                    cands[k] = _Option(
                        name=k,
                        nargs=None,
                        type=_OptionType.SUBPARSER,
                        subparser=v,
                        help=action.help,
                    )
            case _:
                pass
    return cands


def _internal(
    root_parser: argparse.ArgumentParser,
    words: list[str],
    *,
    optional_arg_values: Callable[[str], list[str]] | None = None,
    positional_arg_values: Callable[[str], list[str]] | None = None,
) -> list[str]:
    parserw = _ParserWrapper(root_parser)

    for word in words[:-1]:
        if parserw.nargs_to_read > 0:
            parserw.nargs_to_read -= 1
            continue
        if any(
            option.type == _OptionType.POSITIONAL
            for option in parserw.valid_options.values()
        ):
            # Accept anything for positional.
            parserw.num_positionals_used += 1
            continue
        if word not in parserw.valid_options:
            logging.debug(f"Unknown {word=}")
            return []
        this_option = parserw.valid_options[word]
        if this_option.subparser:
            parserw = _ParserWrapper(this_option.subparser)
        else:
            if this_option.nargs is None:
                logging.debug(
                    f"For non subparsers, nargs cannot be none: {this_option=}"
                )
                return []
            parserw.nargs_to_read = this_option.nargs

    if parserw.nargs_to_read > 0:
        # Look for argument completion.
        if optional_arg_values is None:
            return []
        return optional_arg_values(words[-1])

    # No more throw-away args. Therefore we should show options from valid_options.

    if len(parserw.positionals) > parserw.num_positionals_used:
        # There are more positional args to be passed.
        positional = parserw.positionals[parserw.num_positionals_used]
        # If user started typing "-", return options.
        if words[-1].startswith("-"):
            # Return all OPTIONs, but not SUBPARSERs.
            return parserw.filter_by_types([_OptionType.OPTION])
        # If no function is specified to retrieve positional args, don't hint.
        if positional_arg_values is None:
            return []
        # Else return what values this positional can take.
        return positional_arg_values(positional)

    return parserw.filter_by_types([_OptionType.OPTION, _OptionType.SUBPARSER])


def get_completions(
    root_parser: argparse.ArgumentParser,
    words: list[str],
    *,
    optional_arg_values: Callable[[str], list[str]] | None = None,
    positional_arg_values: Callable[[str], list[str]] | None = None,
) -> list[str]:
    logging.debug(f"Initial args: {words}")

    # Catch all exceptions - since there should be no error during completions.
    try:
        result = _internal(
            root_parser=root_parser,
            words=words,
            optional_arg_values=optional_arg_values,
            positional_arg_values=positional_arg_values,
        )
    except Exception as e:
        logging.error(f"Error during completion: {e}")
        return []

    return [x for x in result if x.startswith(words[-1])]
