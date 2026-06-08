import unittest

from . import app as tui

# Allow importing private methods.
# pyright: reportPrivateUsage=false


class TestAppStartup(unittest.IsolatedAsyncioTestCase):
    """Basic smoke test to ensure the app can be instantiated and initialized."""

    async def test_app_startup(self):
        app = tui._YabsnapApp()
        # run_test() returns an async context manager.
        async with app.run_test() as pilot:
            # We just want to see if it starts without crashing.
            # If it reached here, CSS is valid.
            await pilot.exit(None)

    async def test_app_startup_with_keys(self):
        """Smoke test with show_keys enabled."""
        app = tui._YabsnapApp(show_keys=True)
        async with app.run_test() as pilot:
            self.assertTrue(app._show_keys)
            await pilot.exit(None)


if __name__ == "__main__":
    unittest.main()
