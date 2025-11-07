import unittest

from . import comp_types
from . import shell_impl

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false

_COMPLETIONS: list[comp_types.Completion] = [
    comp_types.Completion(
        option="foo", help="foo help", type=comp_types.CompletionType.COMMAND
    ),
    comp_types.Completion(
        option="--bar", help="bar help", type=comp_types.CompletionType.OPTION
    ),
]


class ShellImplTest(unittest.TestCase):
    def _compare_lines(self, first: str, second: str):
        def normalize(lines: str) -> list[str]:
            return [x.strip() for x in lines.splitlines() if x.strip()]

        self.assertEqual(normalize(first), normalize(second))

    def test_array_completion(self):
        self.assertEqual(shell_impl._array_commands(_COMPLETIONS), "foo --bar")

    def test_bash_completion(self):
        self.assertEqual(
            shell_impl._bash_commands(_COMPLETIONS, file_completions=[]),
            "COMPREPLY=( foo --bar )",
        )

    def test_zsh(self):
        self._compare_lines(
            shell_impl._zsh_commands(
                cur_word="", completions=_COMPLETIONS, file_completions=[], messages=[]
            ),
            """
            local -a yabsnap_commands
            yabsnap_commands=(
              'foo:foo help'
            )
            _describe -t commands 'yabsnap commands' yabsnap_commands

            local -a yabsnap_options
            yabsnap_options=(
              '--bar:bar help'
            )
            _describe -t options 'yabsnap options' yabsnap_options

            compadd -x \'To view flags, type \'"\'"\'-\'"\'"\' and press Tab to complete.'
            compadd -x ''
            """,
        )

    def test_zsh_only_options(self):
        completions = [
            x for x in _COMPLETIONS if x.type == comp_types.CompletionType.OPTION
        ]
        self._compare_lines(
            shell_impl._zsh_commands(
                cur_word="", completions=completions, file_completions=[], messages=[]
            ),
            """
            local -a yabsnap_options
            yabsnap_options=(
              '--bar:bar help'
            )
            _describe -t options 'yabsnap options' yabsnap_options

            compadd -x \'To view flags, type \'"\'"\'-\'"\'"\' and press Tab to complete.'
            compadd -x ''
            """,
        )

    def test_zsh_no_options_correctly_omits_option_help(self):
        completions = [
            x for x in _COMPLETIONS if x.type != comp_types.CompletionType.OPTION
        ]
        self._compare_lines(
            shell_impl._zsh_commands(
                cur_word="", completions=completions, file_completions=[], messages=[]
            ),
            """
            local -a yabsnap_commands
            yabsnap_commands=(
              'foo:foo help'
            )
            _describe -t commands 'yabsnap commands' yabsnap_commands
            """,
        )


if __name__ == "__main__":
    unittest.main()
