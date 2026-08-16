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

The lockfile is deleted after the second boundary or when the process exits (unless
it ends abruptly, e.g. a SIGKILL - but leaving the file is harmless).

Caveats:
  * Best-effort by design: a second that cannot be locked at all (e.g. due to
    file permissions) is rolled over rather than aborting creation, which
    degrades to the older, rarer name-collision behaviour instead of failing.
  * The reservation deliberately tracks the local wall clock, not
    time.monotonic(). This is a project-wide constraint: snapshots are named
    on disk from the wall clock, so the reserved instant (returned to the
    caller) must be the same value they will be created with, or the name
    would not match the creation time. A monotonic reservation would not
    help, since the name it feeds is not comparable with the persisted
    on-disk times. Accepted consequence: if the clock steps backwards (e.g.
    an NTP correction), the same second could be reserved twice.
"""

import contextlib
import datetime
import fcntl
import logging
import os
import threading
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


def _is_same_sec(now: datetime.datetime) -> bool:
    return now.replace(microsecond=0) == datetime.datetime.now().replace(microsecond=0)


def _release_after_second_boundary(fd: int, acquire_time: datetime.datetime) -> None:
    """Ensures lock is held until second-boundary, then releases it."""
    # Careful - if the time is moved back, this must not loop forever (though
    # correctness is no longer guaranteed).
    while _is_same_sec(acquire_time):
        # 0.1 so that it can exit early when the second is over.
        time.sleep(0.1)

    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)

    # We maintain two properties -
    # 1. Locks are guaranteed to be acquired within the same second.
    # 2. Each lock is held at least until the next second boundary.
    # Together these allow us to safely delete old locks.
    with contextlib.suppress(FileNotFoundError, PermissionError):
        os.remove(_lock_file_path(acquire_time))


def _release(fd: int, acquire_time: datetime.datetime) -> None:
    # Return control; but ensure it is held until the second boundary.
    # Not daemon by design - we want to wait until the file is removed.
    threading.Thread(
        target=_release_after_second_boundary, args=(fd, acquire_time)
    ).start()


def _acquire_until(deadline: datetime.datetime) -> tuple[int, datetime.datetime]:
    """Keeps trying the current second, rolling over until a lock is acquired."""
    while True:
        now = datetime.datetime.now()
        fd = _try_acquire(now)

        # Did we move on to the next second while acquiring?
        if not _is_same_sec(now):
            # Acquiring spilled over second boundary. So discard lock from the past.
            if fd is not None:
                # Should be instantaneous despite release_later().
                _release(fd, now)
            # Try again on this second.
            continue

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
        _release(fd, now)
