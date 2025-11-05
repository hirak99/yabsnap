import argparse
import unittest

from . import completions


class CompletionsTest(unittest.TestCase):
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
        self.assertCountEqual(
            completions.get_completions(parser, ["--"]), ["--foo", "--bar"]
        )
        self.assertCountEqual(completions.get_completions(parser, ["--f"]), ["--foo"])
        self.assertCountEqual(
            completions.get_completions(parser, [""]), ["--foo", "--bar", "foo-command"]
        )

        # Test subcommand completions.
        self.assertCountEqual(
            completions.get_completions(parser, ["foo-command", "--"]), ["--baz"]
        )
        self.assertCountEqual(
            completions.get_completions(parser, ["foo-command", "--b"]), ["--baz"]
        )

        # Positional arg produces no result even if there are options.
        self.assertCountEqual(
            completions.get_completions(parser, ["foo-command", ""]), []
        )

        # Test positional argument completions.
        def positional_hints(name: str) -> list[str]:
            self.assertEqual(name, "positional")
            return ["value1-for-positional", "value2-for-positional"]

        self.assertCountEqual(
            completions.get_completions(
                parser, ["foo-command", ""], positional_arg_values=positional_hints
            ),
            ["value1-for-positional", "value2-for-positional"],
        )

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
        self.assertCountEqual(
            completions.get_completions(
                parser, ["foo-command", "any_positional_value", "--"]
            ),
            ["--bar"],
        )

    def test_exceptions_handled(self):
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument(
            "positional",
            type=str,
            help="Positional help.",
        )

        def positional_hints(name: str) -> list[str]:
            self.assertEqual(name, "positional")
            return ["value1"]

        self.assertCountEqual(
            completions.get_completions(
                parser, [""], positional_arg_values=positional_hints
            ),
            ["value1"],
        )

        def positional_hints_with_error(name: str) -> list[str]:
            raise RuntimeError("This error is expected for testing.")

        self.assertCountEqual(
            completions.get_completions(
                parser, [""], positional_arg_values=positional_hints_with_error
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
