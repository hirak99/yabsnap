import argparse
import dataclasses
import functools
import logging

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


@dataclasses.dataclass(frozen=True)
class _Positional:
    name: str


class Completer:

    @functools.cache
    def _get_parser_accepted_args(self, parser: argparse.ArgumentParser):
        # Argument, and how many words to follow.
        accepted: list[tuple[str | _Positional, int | argparse.ArgumentParser]] = []
        for action in parser._actions:
            match action:
                case argparse._HelpAction():  # pyright: ignore
                    accepted += [(x, 0) for x in action.option_strings]
                case argparse._StoreConstAction():  # pyright: ignore
                    accepted += [(x, 0) for x in action.option_strings]
                case argparse._StoreAction():  # pyright: ignore
                    if action.option_strings:
                        accepted += [(x, 1) for x in action.option_strings]
                    else:
                        accepted += [(_Positional(name=action.dest), 1)]
                case argparse._SubParsersAction():  # pyright: ignore
                    accepted += [(k, v) for k, v in action.choices.items()]
                case _:
                    pass
        return {k: v for k, v in accepted}

    from typing import Callable

    def get_completions(
        self,
        root_parser: argparse.ArgumentParser,
        words: list[str],
        optional_arg_values: Callable[[str], list[str]] | None = None,
        positional_arg_values: Callable[[str], list[str]] | None = None,
    ) -> list[str]:
        parser = root_parser
        args = self._get_parser_accepted_args(parser)
        logging.debug(f"Initial args: {words}")
        num_values = 0
        for word in words[:-1]:
            if num_values > 0:
                num_values -= 1
                continue
            if word not in args:
                return []
            need = args[word]
            if isinstance(need, argparse.ArgumentParser):
                parser = need
                args = self._get_parser_accepted_args(parser)
            else:
                num_values = need
        if num_values == 0:
            options: list[str] = []
            positional: _Positional | None = None
            for k in args.keys():
                if isinstance(k, _Positional):
                    positional = k
                else:
                    options.append(k)
            if positional:
                # If user started typing "-", return options.
                if words[-1].startswith("-"):
                    return options
                # If no function is specified to retrieve positional args, don't hint.
                if positional_arg_values is None:
                    return []
                # Else return what values this positional can take.
                return positional_arg_values(words[-1])
            return options
        if optional_arg_values is None:
            return []
        return optional_arg_values(words[-1])
