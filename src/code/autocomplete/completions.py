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
    type: _OptionType
    # None iff type == SUBPARSER.
    nargs: int | None
    # Present iff type == SUBPARSER.
    subparser: argparse.ArgumentParser | None = None


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
                    cands[x] = _Option(name=x, nargs=0, type=_OptionType.OPTION)
            case argparse._StoreAction():  # pyright: ignore
                if action.option_strings:
                    for x in action.option_strings:
                        cands[x] = _Option(name=x, nargs=1, type=_OptionType.OPTION)
                else:
                    cands[action.dest] = _Option(
                        name=action.dest, nargs=0, type=_OptionType.POSITIONAL
                    )
            case argparse._SubParsersAction():  # pyright: ignore
                for k, v in action.choices.items():
                    cands[k] = _Option(
                        name=k, nargs=None, type=_OptionType.SUBPARSER, subparser=v
                    )
            case _:
                pass
    return cands


def get_completions(
    root_parser: argparse.ArgumentParser,
    words: list[str],
    *,
    optional_arg_values: Callable[[str], list[str]] | None = None,
    positional_arg_values: Callable[[str], list[str]] | None = None,
) -> list[str]:
    logging.debug(f"Initial args: {words}")

    def internal():
        parser = root_parser
        valid_options = _get_parser_accepted_args(parser)
        nargs_to_read: int = 0

        for word in words[:-1]:
            if nargs_to_read > 0:
                nargs_to_read -= 1
                continue
            if any(
                option.type == _OptionType.POSITIONAL
                for option in valid_options.values()
            ):
                # Accept anything for positional.
                continue
            if word not in valid_options:
                logging.debug(f"Unknown {word=}")
                return []
            this_option = valid_options[word]
            if this_option.subparser:
                parser = this_option.subparser
                valid_options = _get_parser_accepted_args(parser)
            else:
                if this_option.nargs is None:
                    logging.debug(
                        f"For non subparsers, nargs cannot be none: {this_option=}"
                    )
                    return []
                nargs_to_read = this_option.nargs

        if nargs_to_read == 0:
            options: list[str] = []
            positional: str | None = None
            for cand in valid_options.values():
                if cand.type in {_OptionType.OPTION, _OptionType.SUBPARSER}:
                    options.append(cand.name)
                elif cand.type == _OptionType.POSITIONAL:
                    positional = cand.name
                else:
                    logging.warning(f"Unhandled option type: {cand.type}")

            if positional:
                # If user started typing "-", return options.
                if words[-1].startswith("-"):
                    return options
                # If no function is specified to retrieve positional args, don't hint.
                if positional_arg_values is None:
                    return []
                # Else return what values this positional can take.
                return positional_arg_values(positional)
            return options
        if optional_arg_values is None:
            return []
        return optional_arg_values(words[-1])

    # Catch all exceptions - since there should be no error during completions.
    try:
        result = internal()
    except Exception as e:
        logging.error(f"Error during completion: {e}")
        return []

    return [x for x in result if x.startswith(words[-1])]
