import logging
import os
import shlex

from . import comp_types

# Note - There seems no good way to complete only files in bash. Even if we complete
# dirs, bash will move the cursor forward. We could search with **/*, but that will
# recursively scan entire filesystem.
#
# This is similar to r"COMPREPLY=( $(compgen -f) )", except it adds a "/" to all dirs.
_BASH_COMPREPLY_FILES = r"""
local cur="${COMP_WORDS[COMP_CWORD]}"
local item

local candidates=($(compgen -f -- "$cur"))

COMPREPLY=()

for item in "${candidates[@]}"; do
    # Append "/" to all dirs.
    if [[ -d "$item" ]]; then
        [[ "$item" != */ ]] && item+="/"
    fi
    COMPREPLY+=( "$item" )
done
"""


def _zsh_commands(
    completions: list[comp_types.Completion],
    file_completions: list[comp_types.FileCompletion],
    messages: list[comp_types.Message],
) -> str:
    # NOTE:
    # To view documentation on `compadd`, do this -
    # ```sh
    # unalias run-help
    # autoload run-help
    # run-help compadd
    # ```

    if file_completions:
        return "_path_files"

    # Returns lines defining two arres.
    # They are meant to be `eval`-ed.
    command_lines: list[str] = []
    option_lines: list[str] = []
    for x in completions:
        entry = x.option
        if x.help:
            entry += f":{x.help}"
        if x.type == comp_types.CompletionType.COMMAND:
            command_lines.append(entry)
        elif x.type == comp_types.CompletionType.OPTION:
            option_lines.append(entry)
        else:
            logging.warning(f"Unknown completion type: {x.type}")

    def describe(tag: str, lines: list[str]) -> list[str]:
        result: list[str] = []
        result += [f"local -a yabsnap_{tag}"]
        result += [f"yabsnap_{tag}=("]
        result += [f"  {shlex.quote(x)}" for x in lines]
        result += [f")"]
        result += [f"_describe -t {tag} 'yabsnap {tag}' yabsnap_{tag}"]
        return result

    sh_lines: list[str] = []
    if command_lines:
        sh_lines += describe("commands", command_lines)
    if option_lines:
        sh_lines += describe("options", option_lines)
    if messages:
        sh_lines += [f"compadd -x {shlex.quote(x.message)}" for x in messages]

    return "\n".join(sh_lines)


def _array_commands(
    completions: list[comp_types.Completion],
) -> str:
    # Return array of words. Good for testing.
    return " ".join(x.option for x in completions)


def _bash_commands(
    completions: list[comp_types.Completion],
    file_completions: list[comp_types.FileCompletion],
) -> str:
    if file_completions:
        return _BASH_COMPREPLY_FILES
    words_str = " ".join(f"{shlex.quote(x.option)}" for x in completions)
    return f"COMPREPLY=( {words_str} )"


def shell_commands(
    completions: list[comp_types.Completion],
    file_completions: list[comp_types.FileCompletion],
    messages: list[comp_types.Message],
) -> str:
    style = os.environ.get("STYLE", "")
    match style:
        case "zsh":
            return _zsh_commands(completions, file_completions, messages)
        case "array":
            return _array_commands(completions)
        case "bash":
            return _bash_commands(completions, file_completions)
        case _:
            logging.warning(f"STYLE not provided or is unknown: {style=}")
            return ""
