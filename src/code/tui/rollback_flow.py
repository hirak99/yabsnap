"""Rollback workflow for the TUI: preview, confirm, execute, report."""

import contextlib
import logging
import subprocess
from collections.abc import Awaitable, Generator

from textual import app

from .. import configs
from ..snapshot_logic import rollbacker
from ..utils import script_exec
from . import screens


class _WarningCollector(logging.Handler):
    """logging.Handler storing formatted warnings for display in the TUI."""

    def __init__(self, store: list[str]) -> None:
        super().__init__(level=logging.WARNING)
        self._store: list[str] = store

    def emit(self, record: logging.LogRecord) -> None:
        self._store.append(record.getMessage())


@contextlib.contextmanager
def _captured_warnings() -> Generator[list[str]]:
    """Collects warnings logged while generating the rollback script.

    Library code reports generation-time caveats (e.g. checks skipped without
    sudo) via logging, which is invisible under the TUI's alternate screen.
    Callers can surface the collected lines in a modal instead.

    While capturing, the root logger's own handlers are detached (and
    `lastResort` neutralized for entry points without logging setup), so a
    captured warning is shown exactly once, in the modal, instead of also
    flashing on stderr behind the TUI.
    """
    collected: list[str] = []
    handler = _WarningCollector(collected)
    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    for old_handler in saved_handlers:
        root.removeHandler(old_handler)
    saved_last_resort = logging.lastResort
    logging.lastResort = logging.NullHandler()
    root.addHandler(handler)
    try:
        yield collected
    finally:
        root.removeHandler(handler)
        for old_handler in saved_handlers:
            root.addHandler(old_handler)
        logging.lastResort = saved_last_resort


class RollbackFlow:
    """Owns the multi-step rollback interaction and its running state."""

    def __init__(self, host: app.App[None]) -> None:
        self._host: app.App[None] = host
        self._running: bool = False

    @property
    def is_running(self) -> bool:
        """Whether a rollback script is currently executing."""
        return self._running

    def request(self, config: configs.Config | None, target_path: str | None) -> None:
        """Previews the rollback script for `target_path`, then confirms."""
        if config is None:
            return
        if self._running:
            self._host.notify("Rollback already in progress.", severity="warning")
            return
        if target_path is None:
            return

        with _captured_warnings() as generation_warnings:
            script_text: str | None = rollbacker.get_rollback_script_text(
                [config], target_path, subvol_map=None
            )
        if not script_text:
            self._host.notify("Could not generate rollback script", severity="error")
            return

        def on_confirm(confirmed: bool | None) -> None:
            if not confirmed:
                return None
            self._running = True
            # Defer: this callback runs inside the preview screen's message
            # handler, and pushing a screen from here (or from a worker started
            # here) would target the dismissed screen's message pump.
            self._host.call_after_refresh(self._start, script_text)

        self._host.push_screen(
            screens.RollbackPreviewModal(script_text, warnings=generation_warnings),
            on_confirm,
        )

    def _start(self, script_text: str) -> None:
        modal = screens.RollbackResultModal()
        mount_complete = self._host.push_screen(modal)
        self._host.run_worker(
            self._execute(script_text, modal, mount_complete),
            name="rollback",
            exclusive=True,
        )

    async def _execute(
        self,
        script_text: str,
        modal: screens.RollbackResultModal,
        mount_complete: Awaitable[object],
    ) -> None:
        """Runs the rollback script, streaming its output into `modal`."""
        try:
            # Ensure the modal is mounted before any output is written; the
            # modal also buffers lines, in case children mount a bit later.
            await mount_complete
            executed = await script_exec.execute_streaming(
                script_text, modal.append_line
            )
        except script_exec.ScriptExecutionError as e:
            if rollbacker.is_hook_failure(e):
                modal.finish(
                    "Post-rollback hook failed (core rollback completed). "
                    "Reboot to finish the rollback.",
                    error=True,
                )
            else:
                returncode = (
                    e.cause.returncode
                    if isinstance(e.cause, subprocess.CalledProcessError)
                    else "?"
                )
                modal.finish(f"Rollback FAILED (exit code {returncode}).", error=True)
        except Exception as e:
            modal.finish(f"Unexpected error: {e!s}", error=True)
        else:
            if executed:
                modal.finish("Rollback script executed. Please reboot.")
            else:
                modal.finish("Dry run: the script was not executed.")
        finally:
            self._running = False
