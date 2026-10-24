import datetime
import subprocess
import unittest
from unittest import mock

from textual import widgets

from ..utils import human_interval
from . import screens
from . import tui_app

# Allow importing private methods.
# pyright: reportPrivateUsage=false


class TestSnapshotRow(unittest.TestCase):
    """Table row formatting, independent of the running app."""

    def _snap(
        self, *, trigger: str, expiry: float | None, comment: str = ""
    ) -> mock.MagicMock:
        snap = mock.MagicMock()
        snap.snaptime = datetime.datetime(2022, 1, 1, 13, 0, 0)
        snap.metadata.trigger = trigger
        snap.metadata.expiry = expiry
        snap.metadata.comment = comment
        return snap

    def test_trigger_is_shown_as_a_flag(self):
        now = datetime.datetime(2022, 1, 1, 13, 0, 0)
        snap = self._snap(trigger="U", expiry=None, comment="hello")

        row = tui_app._snapshot_row(snap, now)

        self.assertEqual(row[0], "2022-01-01 13:00:00")
        self.assertEqual(row[1], "--U")
        self.assertEqual(row[2], human_interval.humanize(0))
        self.assertEqual(row[3], "")
        self.assertEqual(row[4], "hello")

    def test_unknown_trigger_shows_no_flags(self):
        now = datetime.datetime(2022, 1, 1, 13, 0, 0)

        row = tui_app._snapshot_row(self._snap(trigger="", expiry=None), now)

        self.assertEqual(row[1], "---")

    def test_age_and_ttl(self):
        snap = self._snap(trigger="S", expiry=None)
        now = snap.snaptime + datetime.timedelta(hours=2)
        snap.metadata.expiry = (snap.snaptime + datetime.timedelta(hours=5)).timestamp()

        row = tui_app._snapshot_row(snap, now)

        self.assertEqual(row[2], human_interval.humanize(2 * 3600))
        self.assertEqual(row[3], human_interval.humanize(3 * 3600))


class TestCreateSnapshot(unittest.IsolatedAsyncioTestCase):
    async def test_create_calls_post_hooks(self):
        app = tui_app._YabsnapApp()
        # Keep the test hermetic: do not load real configs, since selecting one
        # asynchronously overwrites _current_config on mount.
        with mock.patch.object(
            tui_app.configs, "iterate_configs", return_value=iter([])
        ):
            async with app.run_test() as pilot:
                config_mock = mock.MagicMock()
                config_mock.source = "/fake/source"
                app._current_config = config_mock

                with (
                    mock.patch.object(
                        tui_app.snap_operator, "SnapOperator"
                    ) as snapper_cls,
                    mock.patch.object(
                        tui_app.snap_operator,
                        "get_existing_snaps",
                        return_value=iter([]),
                    ),
                ):
                    app.action_create_snapshot()
                    await pilot.pause()
                    await pilot.click("#create")
                    await pilot.pause()

                snapper_cls.return_value.create.assert_called_once_with("")
                config_mock.call_post_hooks.assert_called_once()


class TestSnapshotSelection(unittest.IsolatedAsyncioTestCase):
    """Actions acting on one snapshot behave the same with no snapshot at all."""

    async def _run_with_empty_table(self, action) -> None:
        app = tui_app._YabsnapApp()
        with mock.patch.object(
            tui_app.configs, "iterate_configs", return_value=iter([])
        ):
            async with app.run_test() as pilot:
                with mock.patch.object(
                    tui_app.snap_operator, "get_existing_snaps", return_value=[]
                ):
                    app._current_config = mock.MagicMock()
                    app._refresh_snapshots()
                    await pilot.pause()

                    table = app.query_one("#snapshot-table", widgets.DataTable)
                    self.assertEqual(table.row_count, 0)

                    with mock.patch.object(app, "notify") as notify:
                        action(app)
                        await pilot.pause()

                    notify.assert_called_once_with(
                        "No snapshot selected", severity="warning"
                    )
                    # Nothing was pushed: the action bailed out before its modal.
                    self.assertEqual(len(app.screen_stack), 1)

    async def test_delete_without_snapshot_notifies(self):
        await self._run_with_empty_table(lambda app: app.action_delete_snapshot())

    async def test_rollback_without_snapshot_notifies(self):
        await self._run_with_empty_table(lambda app: app.action_rollback())

    async def test_rollback_without_snapshot_does_not_build_a_script(self):
        app = tui_app._YabsnapApp()
        with mock.patch.object(
            tui_app.configs, "iterate_configs", return_value=iter([])
        ):
            async with app.run_test() as pilot:
                with (
                    mock.patch.object(
                        tui_app.snap_operator, "get_existing_snaps", return_value=[]
                    ),
                    mock.patch.object(
                        tui_app.rollbacker, "get_rollback_script_text"
                    ) as mock_script,
                ):
                    app._current_config = mock.MagicMock()
                    app._refresh_snapshots()
                    await pilot.pause()

                    app.action_rollback()
                    await pilot.pause()

                    mock_script.assert_not_called()


class TestAppStartup(unittest.IsolatedAsyncioTestCase):
    """Basic smoke test to ensure the app can be instantiated and initialized."""

    async def test_app_startup(self):
        app = tui_app._YabsnapApp()
        # run_test() returns an async context manager.
        async with app.run_test() as pilot:
            # We just want to see if it starts without crashing.
            # If it reached here, CSS is valid.
            await pilot.exit(None)

    async def test_app_startup_with_keys(self):
        """Smoke test with show_keys enabled."""
        app = tui_app._YabsnapApp(show_keys=True)
        async with app.run_test() as pilot:
            self.assertTrue(app._show_keys)
            await pilot.exit(None)


class TestRollbackResultModal(unittest.IsolatedAsyncioTestCase):
    """Rollback output is presented in the TUI, for success and failure alike."""

    def _fake_snap(self) -> mock.MagicMock:
        snap = mock.MagicMock()
        snap.snaptime = datetime.datetime.now()
        snap.metadata.trigger = "U"
        snap.metadata.expiry = None
        snap.metadata.comment = ""
        snap.target = "/fake/snap-20220101130000"
        return snap

    async def _run_rollback(self, fake_execute, check) -> None:
        """Drives preview -> confirm -> result modal, then runs `check`."""
        app = tui_app._YabsnapApp()
        with mock.patch.object(
            tui_app.configs, "iterate_configs", return_value=iter([])
        ):
            async with app.run_test() as pilot:
                with (
                    mock.patch.object(
                        tui_app.snap_operator,
                        "get_existing_snaps",
                        return_value=[self._fake_snap()],
                    ),
                    mock.patch.object(
                        tui_app.rollbacker,
                        "get_rollback_script_text",
                        return_value="#!/bin/bash",
                    ),
                    mock.patch.object(
                        tui_app.rollbacker,
                        "execute_script_streaming",
                        side_effect=fake_execute,
                    ),
                ):
                    app._current_config = mock.MagicMock()
                    app._refresh_snapshots()
                    app.action_rollback()
                    await pilot.pause()
                    await pilot.click("#confirm")
                    await app.workers.wait_for_complete()
                    await pilot.pause()
                    check(app.screen, app)

    async def test_success_shows_streamed_output(self):
        async def fake_execute(script_text: str, on_output) -> bool:
            on_output("line one")
            on_output("Please reboot")
            return True

        def check(current_screen, app) -> None:
            self.assertIsInstance(current_screen, screens.RollbackResultModal)
            log = current_screen.query_one("#rollback-log", widgets.RichLog)
            self.assertEqual(
                [strip.text for strip in log.lines], ["line one", "Please reboot"]
            )
            status = current_screen.query_one("#rollback-status", widgets.Label)
            self.assertIn("Please reboot", str(status.render()))
            self.assertFalse(status.has_class("-error"))
            close_button = current_screen.query_one("#close", widgets.Button)
            self.assertFalse(close_button.disabled)
            self.assertFalse(app._rollback_running)

        await self._run_rollback(fake_execute, check)

    async def test_failure_shows_output_and_error_style(self):
        async def fake_execute(script_text: str, on_output) -> bool:
            on_output("btrfs: device not found")
            cause = subprocess.CalledProcessError(
                1, "yabsnap_script.sh", output="btrfs: device not found"
            )
            raise tui_app.rollbacker.RollbackExecutionError(cause)

        def check(current_screen, app) -> None:
            log = current_screen.query_one("#rollback-log", widgets.RichLog)
            self.assertEqual(
                [strip.text for strip in log.lines], ["btrfs: device not found"]
            )
            status = current_screen.query_one("#rollback-status", widgets.Label)
            self.assertIn("FAILED", str(status.render()))
            self.assertIn("exit code 1", str(status.render()))
            self.assertTrue(status.has_class("-error"))
            self.assertTrue(
                current_screen.query_one("#rollback-dialog").has_class("-error")
            )
            self.assertFalse(app._rollback_running)

        await self._run_rollback(fake_execute, check)

    async def test_hook_failure_is_reported_distinctly(self):
        async def fake_execute(script_text: str, on_output) -> bool:
            on_output("post-rollback hook failed (exit 3): /usr/local/bin/hook.sh")
            cause = subprocess.CalledProcessError(
                tui_app.rollbacker._HOOK_FAILURE_CODE, "yabsnap_script.sh"
            )
            raise tui_app.rollbacker.RollbackExecutionError(cause)

        def check(current_screen, app) -> None:
            status = current_screen.query_one("#rollback-status", widgets.Label)
            message = str(status.render())
            self.assertIn("Post-rollback hook failed", message)
            self.assertIn("core rollback completed", message)

        await self._run_rollback(fake_execute, check)


if __name__ == "__main__":
    unittest.main()
