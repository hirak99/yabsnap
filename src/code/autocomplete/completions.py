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

from . import comp_types
from . import shell_impl

from typing import Callable, Sequence


class _OptionType(enum.Enum):
    OPTION = 1
    SUBPARSER = 2
    POSITIONAL = 3


@dataclasses.dataclass(frozen=True)
class _Option:
    option: str
    help: str | None
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
                    cands[x] = _Option(
                        option=x, nargs=0, type=_OptionType.OPTION, help=action.help
                    )
            case argparse._StoreAction():  # pyright: ignore
                if action.option_strings:
                    for x in action.option_strings:
                        cands[x] = _Option(
                            option=x, nargs=1, type=_OptionType.OPTION, help=action.help
                        )
                else:
                    cands[action.dest] = _Option(
                        option=action.dest,
                        nargs=0,
                        type=_OptionType.POSITIONAL,
                        help=action.help,
                    )
            case argparse._SubParsersAction():  # pyright: ignore
                for subaction in action._get_subactions():
                    cands[subaction.dest] = _Option(
                        option=subaction.dest,
                        nargs=None,
                        type=_OptionType.SUBPARSER,
                        subparser=action.choices[subaction.dest],
                        help=subaction.help,
                    )
            case _:
                pass
    return cands


@dataclasses.dataclass
class _ParserWrapper:
    """Convenience class to bookkeep parser related fields."""

    parser: argparse.ArgumentParser
    nargs_to_read: int = 0
    num_positionals_used: int = 0

    def __post_init__(self):
        self.valid_options = _get_parser_accepted_args(self.parser)
        self.positionals: list[_Option] = [
            x for x in self.valid_options.values() if x.type == _OptionType.POSITIONAL
        ]
        logging.debug(f"{len(self.positionals)=}")

    def filter_by_types(self, types: list[_OptionType]) -> list[comp_types.Completion]:
        result: list[comp_types.Completion] = []
        for x in self.valid_options.values():
            if x.type in types:
                result.append(
                    comp_types.Completion(
                        option=x.option,
                        help=x.help,
                        type=(
                            comp_types.CompletionType.OPTION
                            if x.type == _OptionType.OPTION
                            else comp_types.CompletionType.COMMAND
                        ),
                    )
                )
        return result


def _internal(
    root_parser: argparse.ArgumentParser,
    words: list[str],
    *,
    dynamic_args_fn: (
        Callable[[str, int], Sequence[comp_types.AnyCompletionType]] | None
    ),
) -> Sequence[comp_types.AnyCompletionType]:
    parserw = _ParserWrapper(root_parser)

    # If args are being read, which option they are for.
    last_named_arg: _Option | None = None
    if parserw.positionals:
        last_named_arg = parserw.positionals[0]

    # Index of options for the arg.
    arg_index = 0

    for word in words[:-1]:
        if parserw.nargs_to_read > 0:
            parserw.nargs_to_read -= 1
            arg_index += 1
            continue
        last_named_arg = None  # Not known yet, fill in below.
        arg_index = 0

        if len(parserw.positionals) > parserw.num_positionals_used:
            logging.debug(f"Positional arg: {word}")
            last_named_arg = parserw.positionals[parserw.num_positionals_used]
            parserw.num_positionals_used += 1
            continue
        elif word not in parserw.valid_options:
            logging.debug(f"Unknown {word=}")
            return []
        this_option = parserw.valid_options[word]
        last_named_arg = this_option

        if this_option.subparser:
            parserw = _ParserWrapper(this_option.subparser)
        else:
            if this_option.nargs is None:
                logging.debug(
                    f"For non subparsers, nargs cannot be none: {this_option=}"
                )
                return []
            parserw.nargs_to_read = this_option.nargs

    def get_dyn_options() -> Sequence[comp_types.AnyCompletionType]:
        def format_help(name: str, help: str | None) -> str:
            message = name
            if help:
                message += f": {help}"
            return message

        if last_named_arg is None:
            logging.warning(f"last_named_arg is None for {words=}")
            return []

        # If positional, name of the arg e.g. 'target_suffix'.
        # If value of an arg, name of the option e.g. '--source'.
        arg_name: str | None = None
        arg_help: str | None = None

        if last_named_arg.subparser:
            positional_actions = last_named_arg.subparser._get_positional_actions()
            if len(positional_actions) > arg_index:
                positional_arg = positional_actions[arg_index]
                arg_name = positional_arg.dest
                arg_help = positional_arg.help
        if arg_name is None:
            arg_name = last_named_arg.option
            arg_help = last_named_arg.help

        if dynamic_args_fn is not None:
            result = dynamic_args_fn(arg_name, arg_index)
            if result:
                return result

        return [comp_types.Message(format_help(arg_name, arg_help))]

    if parserw.nargs_to_read > 0:
        # Look for argument completion.
        logging.debug(f"Argument expected for {last_named_arg}")
        if dynamic_args_fn is None:
            return []
        return get_dyn_options()

    # No more throw-away args. Therefore we should show options from valid_options.
    if len(parserw.positionals) > parserw.num_positionals_used:
        # There are positional args to be passed.
        # If user started typing "-", return options.
        if words[-1].startswith("-"):
            # Return all OPTIONs, but not SUBPARSERs.
            return parserw.filter_by_types([_OptionType.OPTION])
        # If no function is specified to retrieve positional args, don't hint.
        return get_dyn_options()

    return parserw.filter_by_types([_OptionType.OPTION, _OptionType.SUBPARSER])


def _get_shell_commands(
    candidates: Sequence[comp_types.AnyCompletionType],
    *,
    ignore_args: set[str] | None = None,
    cur_word: str,
) -> str:
    completions: list[comp_types.Completion] = []
    special_completions: list[comp_types.FileCompletion] = []
    messages: list[comp_types.Message] = []
    for x in candidates:
        if isinstance(x, comp_types.FileCompletion):
            special_completions.append(x)
        elif isinstance(x, str):
            completions.append(
                comp_types.Completion(
                    option=x, help=None, type=comp_types.CompletionType.COMMAND
                )
            )
        elif isinstance(x, comp_types.Message):
            messages.append(x)
        else:
            completions.append(x)

    completions = [
        x
        for x in completions
        if (not ignore_args or x.option not in ignore_args)
        and x.option.startswith(cur_word)
    ]

    return shell_impl.shell_commands(completions, special_completions, messages)


def get_completions(
    root_parser: argparse.ArgumentParser,
    words: list[str],
    *,
    dynamic_args_fn: (
        Callable[[str, int], Sequence[comp_types.AnyCompletionType]] | None
    ) = None,
    ignore_args: set[str] | None = None,
) -> str:
    logging.debug(f"Initial args: {words}")

    # Catch all exceptions - since there should be no error during completions.
    try:
        candidates = _internal(
            root_parser=root_parser,
            words=words,
            dynamic_args_fn=dynamic_args_fn,
        )
    except Exception as e:
        logging.error(f"Error during completion: {e}")
        return ""

    return _get_shell_commands(candidates, ignore_args=ignore_args, cur_word=words[-1])
