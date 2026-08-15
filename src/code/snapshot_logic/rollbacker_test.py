import builtins
import os
import tempfile
import unittest
from unittest import mock

from .. import global_flags
from ..utils import os_utils
from . import rollbacker

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false


class TestCreateAndChmodScript(unittest.TestCase):
    def test_rollback_no_execute(self):
        with (
            mock.patch.object(rollbacker, "get_rollback_script_text") as mock_script,
            mock.patch.object(builtins, "print") as mock_print,
            mock.patch.object(rollbacker, "save_and_execute_script") as mock_execute,
        ):
            mock_script.return_value = "echo Rollback"
            rollbacker.rollback(configs_iter=[], path_suffix="", subvol_map=None)

        mock_print.assert_called_once_with("echo Rollback")
        mock_execute.assert_not_called()

    def test_rollback_execute_noconfirm(self):
        with tempfile.TemporaryDirectory() as dir:
            target_file = os.path.join(dir, "test_file")
            script_content = "\n".join(["#!/bin/bash", f"touch {target_file}"])
            with mock.patch.object(
                rollbacker, "get_rollback_script_text"
            ) as mock_script:
                mock_script.return_value = script_content
                rollbacker.rollback(
                    configs_iter=[],
                    path_suffix="",
                    subvol_map=None,
                    execute=True,
                    no_confirm=True,
                )
                # If the script ran, this file would be created.
                self.assertTrue(os.path.exists(target_file))

    def test_rollback_noexecute_on_confirm_failure(self):
        with tempfile.TemporaryDirectory() as dir:
            target_file = os.path.join(dir, "test_file")
            script_content = "\n".join(["#!/bin/bash", f"touch {target_file}"])
            with (
                mock.patch.object(
                    rollbacker, "get_rollback_script_text"
                ) as mock_script,
                mock.patch.object(os_utils, "interactive_confirm", return_value=False),
            ):
                mock_script.return_value = script_content
                rollbacker.rollback(
                    configs_iter=[],
                    path_suffix="",
                    subvol_map=None,
                    execute=True,
                    no_confirm=False,
                )
                # Script should not run since confirm should return False.
                self.assertFalse(os.path.exists(target_file))

    def test_save_and_execute_script_success(self):
        with tempfile.TemporaryDirectory() as dir:
            target_file = os.path.join(dir, "test_file")
            script_content = "\n".join(["#!/bin/bash", f"touch {target_file}"])
            rollbacker.save_and_execute_script(script_content)
            self.assertTrue(os.path.exists(target_file))

    def test_save_and_execute_script_failure(self):
        script_content = "\n".join(["#!/bin/bash", "exit 3"])
        with self.assertRaisesRegex(
            rollbacker.RollbackExecutionError, "returned non-zero exit status 3"
        ):
            rollbacker.save_and_execute_script(script_content)

    def test_save_and_execute_script_dryrun(self):
        with mock.patch.object(global_flags.FLAGS, "dryrun", True):
            rollbacker.save_and_execute_script("exit 1")

    def test_rollback_exit_on_failure(self):
        script_content = "\n".join(["#!/bin/bash", "exit 1"])
        with mock.patch.object(rollbacker, "get_rollback_script_text") as mock_script:
            mock_script.return_value = script_content
            with self.assertRaises(SystemExit):
                rollbacker.rollback(
                    configs_iter=[],
                    path_suffix="",
                    subvol_map=None,
                    execute=True,
                    no_confirm=True,
                )
