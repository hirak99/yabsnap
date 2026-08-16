"""Best-effort per-second cross-process lock for snapshot creation.

Snapshot names have a granularity of one second (<prefix><YYYYMMDDHHMMSS>) and
independent processes (systemd timer, package manager hook, user or TUI) can
start yabsnap at the same time. To keep two processes from creating a snapshot
with the same name, the step of taking the time and using it for the name must
be serialized across processes. This module does this by reserving one
wall-clock second at a time.

A lock file named yabsnap-<YYYYMMDDHHMMSS> is created in /dev/shm (a tmpfs,
so it is fast and cleared on reboot) and locked with flock(). Only one process
may hold the lock of a second; a process that finds its second already locked
rolls over to the next second, so the wait is normally under a second. The
timeout is a safety net for persistent failures, e.g. /dev/shm being
unavailable, and results in a RuntimeError.

Caveats:
  * Best-effort by design: a second that cannot be locked at all (e.g. due to
    file permissions) is rolled over rather than aborting creation, which
    degrades to the older, rarer name-collision behaviour instead of failing.
  * Lock files are never deleted: one 0-byte file per used second accumulates
    in /dev/shm until reboot, which clears the tmpfs.
  * The reservation is based on the local wall clock. If the clock steps
    backwards (e.g. an NTP correction), the same second could be reserved
    twice.
"""

import contextlib
import datetime
import fcntl
import logging
import os
import time
from collections.abc import Generator

from .. import global_flags

# Lock files live on tmpfs: fast, and automatically cleared on reboot.
_LOCK_DIR = "/dev/shm"
_LOCK_PREFIX = "yabsnap-"
# Give up and raise RuntimeError if the lock cannot be acquired within this.
_DEFAULT_TIMEOUT_SECS = 30
# Seconds to wait before trying the next second.
_RETRY_INTERVAL_SECS = 1


def _lock_file_path(now: datetime.datetime) -> str:
    return os.path.join(
        _LOCK_DIR, _LOCK_PREFIX + now.strftime(global_flags.TIME_FORMAT)
    )


def _try_acquire(now: datetime.datetime) -> int | None:
    """Attempts a non-blocking exclusive flock of the given second.

    Returns:
      The file descriptor if the lock was acquired, otherwise None.
    """
    path = _lock_file_path(now)
    try:
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o666)
    except OSError as exc:
        logging.warning(f"Could not open lock file {path!r}: {exc}")
        return None
    # Make the file accessible to other users regardless of umask, so that
    # every yabsnap process (root or not) can lock the same second.
    with contextlib.suppress(OSError):
        os.fchmod(fd, 0o666)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None
    return fd


def _release(fd: int) -> None:
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)


def _acquire_until(deadline: datetime.datetime) -> tuple[int, datetime.datetime]:
    """Keeps trying the current second, rolling over until a lock is acquired."""
    while True:
        now = datetime.datetime.now()
        fd = _try_acquire(now)
        if fd is not None:
            logging.info(
                f"Reserved snapshot time: {now.strftime(global_flags.TIME_FORMAT)}"
            )
            return fd, now
        if now >= deadline:
            raise RuntimeError(
                "Could not acquire the per-second snapshot lock; "
                "another yabsnap process may be creating snapshots, "
                "or /dev/shm is unavailable."
            )
        time.sleep(_RETRY_INTERVAL_SECS)


@contextlib.contextmanager
def locked_now(
    timeout_secs: float = _DEFAULT_TIMEOUT_SECS,
) -> Generator[datetime.datetime]:
    """Reserves the current wall-clock second for the duration of the with block.

    The yielded time must be used as "now" when creating snapshots, so that
    the snapshot name matches the reserved second.

    Yields:
      The reserved current time.

    Raises:
      RuntimeError: If a lock could not be acquired within timeout_secs.
    """
    begin = datetime.datetime.now()
    deadline = begin + datetime.timedelta(seconds=timeout_secs)
    fd, now = _acquire_until(deadline)
    try:
        yield now
    finally:
        _release(fd)
