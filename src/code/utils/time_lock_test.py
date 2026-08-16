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


# Mock for _release() for the test, release immediately instead of waiting for the
# second boundary; the temp lock dir is cleaned up by setUp's tmp directory.
def _release_immediately(fd: int, now: datetime.datetime) -> None:
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)


class TimeLockTest(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self._lock_dir: str = tmp.name
        patcher = mock.patch.object(time_lock, "_LOCK_DIR", self._lock_dir)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(time_lock, "_release", _release_immediately)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_release_after_second_boundary_releases_and_removes(self) -> None:
        acquire_time = datetime.datetime.now() - datetime.timedelta(seconds=1)
        fd = os.open(_lock_path(acquire_time, self._lock_dir), os.O_CREAT | os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Freeze the (fake) clock just past acquire_time's second boundary, so
        # this must return promptly, releasing the lock and removing the
        # lock file.
        fake_now = acquire_time.replace(microsecond=0) + datetime.timedelta(
            seconds=1, milliseconds=100
        )
        with mock.patch.object(time_lock, "datetime") as fake_datetime:
            fake_datetime.datetime.now.return_value = fake_now
            start = time.monotonic()
            time_lock._release_after_second_boundary(fd, acquire_time)
        self.assertLess(time.monotonic() - start, 1)
        self.assertFalse(os.path.exists(_lock_path(acquire_time, self._lock_dir)))
        with self.assertRaises(OSError):
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

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
