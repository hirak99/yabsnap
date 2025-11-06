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

def shell_commands(
    completions: list[comp_types.Completion],
    file_completions: list[comp_types.FileCompletion],
):
    style = os.environ.get("STYLE", "")
    if style == "zsh":
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

        def surround(varname: str, lines: list[str]) -> list[str]:
            result: list[str] = []
            result += [f"local -a {varname}"]
            result += [f"{varname}=("]
            result += [f"  '{x}'" for x in lines]
            result += [f")"]
            return result

        return "\n".join(
            surround("yabsnap_commands", command_lines)
            + surround("yabsnap_options", option_lines)
            + [
                "_describe -t commands 'yabsnap command' yabsnap_commands",
                "_describe -t options 'yabsnap options' yabsnap_options",
            ]
        )

    if style == "array":
        # Return array of words. Good for testing.
        return " ".join(x.option for x in completions)

    if style == "bash":
        # Return commands to be eval'ed in bash.
        if file_completions:
            return _BASH_COMPREPLY_FILES
        words_str = " ".join(f"{shlex.quote(x.option)}" for x in completions)
        return f"COMPREPLY=( {words_str} )"

    logging.warning(f"STYLE not provided or is unknown: {style=}")
    return ""
