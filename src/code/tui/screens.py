from textual import app
from textual import containers
from textual import events
from textual import screen
from textual import widgets

from typing import Literal


class CreateModal(screen.ModalScreen[str | None]):
    """A modal for entering a snapshot comment."""

    CSS_PATH = "screens.tcss"

    def compose(self) -> app.ComposeResult:
        with containers.Vertical(id="dialog"):
            yield widgets.Label("Create User Snapshot", id="dialog-title")
            yield widgets.Label("Optional comment:")
            yield widgets.Input(placeholder="Enter comment...", id="comment-input")
            with containers.Horizontal(id="dialog-buttons"):
                yield widgets.Button("Cancel", variant="error", id="cancel")
                yield widgets.Button("Create", variant="primary", id="create")

    def on_mount(self) -> None:
        self.query_one("#comment-input").focus()

    def on_button_pressed(self, event: widgets.Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        else:
            comment_input: widgets.Input = self.query_one(
                "#comment-input", widgets.Input
            )
            self.dismiss(comment_input.value)

    def on_input_submitted(self, event: widgets.Input.Submitted) -> None:
        self.dismiss(event.value)


# TODO: Can we access the one defined in widgets.Button directly, instead of redefining?
type _ButtonVariant = Literal["primary", "error"]


class ConfirmModal(screen.ModalScreen[bool]):
    """A generic confirmation modal."""

    CSS_PATH = "screens.tcss"

    def __init__(
        self,
        title: str,
        message: str,
        confirm_label: str = "Confirm",
        cancel_label: str = "Cancel",
        variant: _ButtonVariant = "primary",
    ) -> None:
        super().__init__()
        self._title_text: str = title
        self._message_text: str = message
        self._confirm_label: str = confirm_label
        self._cancel_label: str = cancel_label
        self._variant: _ButtonVariant = variant

    def compose(self) -> app.ComposeResult:
        with containers.Vertical(id="dialog"):
            yield widgets.Label(self._title_text, id="dialog-title")
            yield widgets.Static(self._message_text, id="dialog-message")
            with containers.Horizontal(id="dialog-buttons"):
                yield widgets.Button(self._cancel_label, variant="error", id="cancel")
                yield widgets.Button(
                    self._confirm_label, variant=self._variant, id="confirm"
                )

    def on_button_pressed(self, event: widgets.Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)

    async def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss(False)
            event.stop()


class RollbackPreviewModal(screen.ModalScreen[bool]):
    """A modal for previewing a rollback script."""

    CSS_PATH = "screens.tcss"

    def __init__(self, script_text: str) -> None:
        super().__init__()
        self._script_text: str = script_text

    def compose(self) -> app.ComposeResult:
        with containers.Vertical(id="rollback-dialog"):
            yield widgets.Label("Rollback Preview", id="dialog-title")
            yield widgets.Label(
                "Please review the rollback script below before execution."
            )
            yield widgets.Label(
                "Warning: executing this script replaces live system "
                "subvolumes. Review every command below "
                "-- only proceed if you understand what it does.",
                id="rollback-warning",
            )
            yield widgets.TextArea(
                self._script_text, read_only=True, id="rollback-script"
            )
            with containers.Horizontal(id="dialog-buttons"):
                yield widgets.Button("Cancel", variant="error", id="cancel")
                yield widgets.Button(
                    "Execute Rollback", variant="primary", id="confirm"
                )

    def on_button_pressed(self, event: widgets.Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)

    async def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss(False)
            event.stop()


class RollbackResultModal(screen.ModalScreen[None]):
    """A modal showing rollback output live, then its final status.

    Output is fed line by line via append_line(); finish() marks the run as done,
    styles the result (red on failure) and enables the Close button. Lines and
    status that arrive before the widgets are mounted are buffered and applied
    on mount. While running, the modal cannot be dismissed.
    """

    CSS_PATH = "screens.tcss"

    def __init__(self, title: str = "Rollback") -> None:
        super().__init__()
        self._title_text: str = title
        self._finished: bool = False
        self._status_text: str = "Running rollback script..."
        self._status_error: bool = False
        self._pending_lines: list[str] = []
        self._log: widgets.RichLog | None = None

    def compose(self) -> app.ComposeResult:
        with containers.Vertical(id="rollback-dialog"):
            yield widgets.Label(self._title_text, id="dialog-title")
            yield widgets.Label(self._status_text, id="rollback-status")
            yield widgets.RichLog(
                markup=False, highlight=False, wrap=True, id="rollback-log"
            )
            with containers.Horizontal(id="dialog-buttons"):
                yield widgets.Button(
                    "Close", variant="primary", id="close", disabled=not self._finished
                )

    def on_mount(self) -> None:
        self._log = self.query_one("#rollback-log", widgets.RichLog)
        for line in self._pending_lines:
            self._log.write(line)
        self._pending_lines.clear()
        self._apply_status()

    def append_line(self, line: str) -> None:
        if self._log is None:
            self._pending_lines.append(line)
        else:
            self._log.write(line)

    def finish(self, message: str, *, error: bool = False) -> None:
        """Records the final status and allows the modal to be closed."""
        self._finished = True
        self._status_text = message
        self._status_error = error
        self._apply_status()

    def _apply_status(self) -> None:
        if self._log is None:
            # Widgets not mounted yet; on_mount() applies the buffered state.
            return
        status: widgets.Label = self.query_one("#rollback-status", widgets.Label)
        status.update(self._status_text)
        if self._status_error:
            status.add_class("-error")
            self.query_one("#rollback-dialog").add_class("-error")
        close_button: widgets.Button = self.query_one("#close", widgets.Button)
        close_button.disabled = False
        close_button.focus()

    def on_button_pressed(self, event: widgets.Button.Pressed) -> None:
        if event.button.id == "close":
            self.dismiss(None)

    async def on_key(self, event: events.Key) -> None:
        # Not dismissible while the script is still running.
        if event.key == "escape" and self._finished:
            self.dismiss(None)
            event.stop()


class ShowJsonModal(screen.ModalScreen[None]):
    """A modal for displaying JSON metadata."""

    CSS_PATH = "screens.tcss"

    def __init__(self, title: str, json_text: str) -> None:
        super().__init__()
        self._title_text: str = title
        self._json_text: str = json_text

    def compose(self) -> app.ComposeResult:
        with containers.Vertical(id="rollback-dialog"):
            yield widgets.Label(self._title_text, id="dialog-title")
            yield widgets.TextArea(
                self._json_text, read_only=True, id="json-display", language="json"
            )
            with containers.Horizontal(id="dialog-buttons"):
                yield widgets.Button("Close", variant="primary", id="close")

    def on_button_pressed(self, event: widgets.Button.Pressed) -> None:
        self.dismiss(None)

    async def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss()
            event.stop()
