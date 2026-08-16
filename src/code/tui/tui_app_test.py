import unittest
from unittest import mock

from . import tui_app

# Allow importing private methods.
# pyright: reportPrivateUsage=false


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


if __name__ == "__main__":
    unittest.main()
