import unittest
from unittest import mock

from .. import global_flags
from . import script_exec


class TestExecuteStreaming(unittest.IsolatedAsyncioTestCase):
    """execute_streaming(): generic script execution with output capture."""

    async def test_streams_output_in_order(self):
        lines: list[str] = []
        executed = await script_exec.execute_streaming(
            "#!/bin/bash\necho one\necho two", lines.append
        )
        self.assertTrue(executed)
        self.assertEqual(lines, ["one", "two"])

    async def test_failure_captures_merged_output(self):
        lines: list[str] = []
        with self.assertRaises(script_exec.ScriptExecutionError) as ctx:
            await script_exec.execute_streaming(
                "#!/bin/bash\necho before\necho boom >&2\nexit 3", lines.append
            )
        self.assertEqual(lines, ["before", "boom"])
        error = ctx.exception
        self.assertIn("before", error.output)
        self.assertIn("boom", error.output)

    async def test_dryrun_does_not_execute(self):
        lines: list[str] = []
        with mock.patch.object(global_flags.FLAGS, "dryrun", True):
            executed = await script_exec.execute_streaming(
                "#!/bin/bash\nexit 1", lines.append
            )
        self.assertFalse(executed)
        self.assertEqual(len(lines), 1)
        self.assertIn("--dry-run", lines[0])


class TestExecuteSync(unittest.TestCase):
    def test_dryrun_does_not_execute(self):
        with mock.patch.object(global_flags.FLAGS, "dryrun", True):
            self.assertFalse(script_exec.execute_sync("exit 1"))


if __name__ == "__main__":
    unittest.main()
