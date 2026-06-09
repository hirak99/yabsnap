from textual import app
from textual import containers
from textual import events
from textual import screen
from textual import widgets

from typing import Literal


class CreateModal(screen.ModalScreen[str | None]):
    """A modal for entering a snapshot comment."""

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

    def __init__(self, script_text: str) -> None:
        super().__init__()
        self._script_text: str = script_text

    def compose(self) -> app.ComposeResult:
        with containers.Vertical(id="rollback-dialog"):
            yield widgets.Label("Rollback Preview", id="dialog-title")
            yield widgets.Label(
                "Please review the rollback script below before execution."
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


class ShowJsonModal(screen.ModalScreen[None]):
    """A modal for displaying JSON metadata."""

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
