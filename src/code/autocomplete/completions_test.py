import argparse
import os
import unittest
from unittest import mock

from . import completions


class CompletionsTest(unittest.TestCase):
    @mock.patch.dict(os.environ, {"STYLE": "array"})
    def test_completions(self):
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument(
            "--foo",
            type=str,
            help="Foo help.",
        )
        parser.add_argument(
            "--bar",
            type=str,
            help="Bar help.",
        )
        subparsers = parser.add_subparsers(dest="command", title="command", metavar="")
        foo_command = subparsers.add_parser(
            "foo-command", help="Foo command help.", add_help=False
        )
        foo_command.add_argument(
            "--baz",
            type=str,
            help="Baz help.",
        )
        foo_command.add_argument("positional", type=str, help="Positional help.")

        # Test top-level completions.
        self.assertEqual(completions.get_completions(parser, ["--"]), "--foo --bar")
        self.assertEqual(completions.get_completions(parser, ["--f"]), "--foo")
        self.assertEqual(
            completions.get_completions(parser, [""]), "--foo --bar foo-command"
        )

        # Test subcommand completions.
        self.assertEqual(
            completions.get_completions(parser, ["foo-command", "--"]), "--baz"
        )
        self.assertEqual(
            completions.get_completions(parser, ["foo-command", "--b"]), "--baz"
        )

        # Positional arg produces no result even if there are options.
        self.assertEqual(completions.get_completions(parser, ["foo-command", ""]), "")

        # Test positional argument completions.
        def positional_hints(option: str, arg_index: int) -> list[str]:
            self.assertEqual(option, "positional")
            return ["common", f"value{arg_index}"]

        self.assertEqual(
            completions.get_completions(
                parser, ["foo-command", ""], dynamic_args=positional_hints
            ),
            "common value0",
        )

    @mock.patch.dict(os.environ, {"STYLE": "array"})
    def test_positional_acceptance(self):
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument(
            "positional",
            type=str,
            help="Positional help.",
        )
        parser.add_argument(
            "--bar",
            type=str,
            help="Bar help.",
        )

        # Test that options are generated after positional.
        self.assertEqual(
            completions.get_completions(
                parser, ["foo-command", "any_positional_value", "--"]
            ),
            "--bar",
        )

        # After the positional is used up, it now shows options.
        self.assertEqual(
            completions.get_completions(
                parser, ["foo-command", "any_positional_value", ""]
            ),
            "--bar",
        )

    @mock.patch.dict(os.environ, {"STYLE": "array"})
    def test_exceptions_handled(self):
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument(
            "positional",
            type=str,
            help="Positional help.",
        )

        def positional_hints(option: str, arg_index) -> list[str]:
            self.assertEqual(option, "positional")
            return ["value1"]

        self.assertEqual(
            completions.get_completions(parser, [""], dynamic_args=positional_hints),
            "value1",
        )

        def positional_hints_with_error(option: str, arg_index) -> list[str]:
            raise RuntimeError("This error is expected for testing.")

        self.assertEqual(
            completions.get_completions(
                parser, [""], dynamic_args=positional_hints_with_error
            ),
            "",
        )

    @mock.patch.dict(os.environ, {"STYLE": "bash"})
    def test_bash(self):
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument(
            "--arg1",
            type=str,
            help="Arg1 help.",
        )

        self.assertEqual(
            completions.get_completions(parser, ["--"]), "COMPREPLY=( --arg1 )"
        )

    @mock.patch.dict(os.environ, {"STYLE": "zsh"})
    def test_zsh(self):
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument(
            "--arg1",
            type=str,
            help="Arg1 help.",
        )

        self.assertEqual(
            completions.get_completions(parser, ["--"]).splitlines(),
            [
                "local -a yabsnap_commands",
                "yabsnap_commands=(",
                ")",
                "local -a yabsnap_options",
                "yabsnap_options=(",
                "  '--arg1:Arg1 help.'",
                ")",
                "_describe -t commands 'yabsnap command' yabsnap_commands",
                "_describe -t options 'yabsnap options' yabsnap_options",
            ],
        )


if __name__ == "__main__":
    unittest.main()
