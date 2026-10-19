import builtins
import os
import tempfile
import unittest
from unittest import mock

from .. import configs
from .. import global_flags
from ..mechanisms import snap_mechanisms
from ..mechanisms import snap_type_enum
from ..utils import os_utils
from . import rollbacker
from . import snap_operator

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


class TestPostRollbackHooks(unittest.TestCase):
    def _fake_config(self, config_file, snap_type, scripts):
        return configs.Config(
            config_file=config_file,
            source="/",
            dest_prefix="/.snapshots/@root-",
            snap_type=snap_type,
            post_rollback_scripts=scripts,
        )

    def _fake_snap(self, target):
        snap = mock.Mock()
        snap.target = target
        snap.to_light_snapshot.return_value = mock.Mock()
        return snap

    def test_no_hooks_no_extra_lines(self):
        config = self._fake_config(
            "/etc/yabsnap/configs/root.conf", snap_type_enum.SnapType.BTRFS, []
        )
        snap = self._fake_snap("/.snapshots/@root-20220101130000")
        with (
            mock.patch.object(snap_operator, "find_target", return_value=snap),
            mock.patch.object(snap_mechanisms, "get") as mock_get,
        ):
            mock_get.return_value.rollback_gen.return_value = ["echo rollback"]
            text = rollbacker.get_rollback_script_text([config], "suffix", None)
        assert text is not None
        self.assertIn("echo rollback", text)
        self.assertNotIn("YABSNAP_SNAPSHOT_PATH", text)

    def test_hooks_embedded_with_config_and_snapshot(self):
        config = self._fake_config(
            "/etc/yabsnap/configs/root.conf",
            snap_type_enum.SnapType.BTRFS,
            ["/usr/local/bin/restore-efi.sh"],
        )
        target = "/.snapshots/@root-20220101130000"
        snap = self._fake_snap(target)
        with (
            mock.patch.object(snap_operator, "find_target", return_value=snap),
            mock.patch.object(snap_mechanisms, "get") as mock_get,
        ):
            mock_get.return_value.rollback_gen.return_value = ["echo rollback"]
            text = rollbacker.get_rollback_script_text([config], "suffix", None)
        assert text is not None
        # Core rollback comes first, hooks after.
        self.assertLess(text.index("echo rollback"), text.index("restore-efi.sh"))
        self.assertIn(
            "YABSNAP_SNAPSHOT_PATH=/.snapshots/@root-20220101130000 "
            "/usr/local/bin/restore-efi.sh "
            "/etc/yabsnap/configs/root.conf "
            "/.snapshots/@root-20220101130000",
            text,
        )

    def test_hooks_quoted_and_per_config(self):
        config1 = self._fake_config(
            "/etc/yabsnap/configs/root.conf",
            snap_type_enum.SnapType.BTRFS,
            ["/my dir/hook.sh"],
        )
        config2 = self._fake_config(
            "/etc/yabsnap/configs/home.conf",
            snap_type_enum.SnapType.BTRFS,
            [],
        )
        snap1 = self._fake_snap("/.snapshots/@root-20220101130000")
        snap2 = self._fake_snap("/.snapshots/@home-20220101130000")
        with (
            mock.patch.object(snap_operator, "find_target", side_effect=[snap1, snap2]),
            mock.patch.object(snap_mechanisms, "get") as mock_get,
        ):
            mock_get.return_value.rollback_gen.return_value = ["echo rollback"]
            text = rollbacker.get_rollback_script_text(
                [config1, config2], "suffix", None
            )
        assert text is not None
        # Quoting handles spaces; only config1's hook appears, once.
        self.assertIn("'/my dir/hook.sh'", text)
        self.assertEqual(text.count("/my dir/hook.sh"), 1)
        self.assertIn("root.conf", text)

    def test_no_matching_snapshot_returns_none(self):
        config = self._fake_config(
            "/etc/yabsnap/configs/root.conf",
            snap_type_enum.SnapType.BTRFS,
            ["/usr/local/bin/restore-efi.sh"],
        )
        with mock.patch.object(snap_operator, "find_target", return_value=None):
            self.assertIsNone(
                rollbacker.get_rollback_script_text([config], "suffix", None)
            )
