import io
import logging
import sys
import unittest
from unittest import mock

from . import rollback_flow

# Allow importing private helpers.
# pyright: reportPrivateUsage=false


class TestCapturedWarnings(unittest.TestCase):
    """Generation-time warnings are collected, not flashed on stderr."""

    def test_warning_is_collected_and_not_written_to_stderr(self):
        with (
            mock.patch.object(sys, "stderr", new_callable=io.StringIO) as fake_stderr,
            rollback_flow._captured_warnings() as collected,
        ):
            logging.getLogger().warning("flash?")
        self.assertEqual(collected, ["flash?"])
        self.assertEqual(fake_stderr.getvalue(), "")

    def test_handlers_are_restored_after_capture(self):
        root = logging.getLogger()
        before_handlers = root.handlers[:]
        before_last_resort = logging.lastResort
        with rollback_flow._captured_warnings():
            pass
        self.assertEqual(root.handlers, before_handlers)
        self.assertIs(logging.lastResort, before_last_resort)


if __name__ == "__main__":
    unittest.main()
