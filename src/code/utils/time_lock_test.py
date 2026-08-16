import datetime
import fcntl
import os
import tempfile
import time
import unittest
from unittest import mock

from .. import global_flags
from . import time_lock

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false


def _lock_path(now: datetime.datetime, lock_dir: str) -> str:
    return os.path.join(lock_dir, "yabsnap-" + now.strftime(global_flags.TIME_FORMAT))


class TimeLockTest(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self._lock_dir: str = tmp.name
        patcher = mock.patch.object(time_lock, "_LOCK_DIR", self._lock_dir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_reserves_a_second_and_releases_it(self) -> None:
        with time_lock.locked_now() as now:
            # A lock file must exist for the reserved (yielded) second.
            self.assertTrue(os.path.isfile(_lock_path(now, self._lock_dir)))
            # The same second cannot be reserved again while it is held.
            self.assertIsNone(time_lock._try_acquire(now))
        # After the block the second can be reserved again.
        fd = time_lock._try_acquire(now)
        if fd is None:
            self.fail("Expected the second to be reservable after release.")
        time_lock._release(fd)

    def test_rolls_over_when_current_second_is_locked(self) -> None:
        blocked = datetime.datetime.now()
        blocked_fd = os.open(
            _lock_path(blocked, self._lock_dir), os.O_CREAT | os.O_RDWR
        )
        try:
            fcntl.flock(blocked_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with time_lock.locked_now(timeout_secs=10) as now:
                # The current second is taken, so a later second must be used.
                self.assertGreater(now, blocked)
        finally:
            os.close(blocked_fd)

    def test_raises_when_lock_cannot_be_acquired(self) -> None:
        # Point the lock dir at a path beneath a regular file, so that
        # every attempt to open a lock file fails (ENOTDIR), even as root.
        blocker = os.path.join(self._lock_dir, "afile")
        with open(blocker, "w", encoding="utf-8"):
            pass
        bad_dir = blocker + os.sep + "sub"
        with mock.patch.object(time_lock, "_LOCK_DIR", bad_dir):
            start = time.monotonic()
            with (
                self.assertRaises(RuntimeError),
                time_lock.locked_now(timeout_secs=1.0),
            ):
                self.fail("Expected the lock acquisition to time out.")
            self.assertLess(time.monotonic() - start, 5)


if __name__ == "__main__":
    unittest.main()
