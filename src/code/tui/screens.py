from textual import app
from textual import containers
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
            comment = self.query_one("#comment-input", widgets.Input).value
            self.dismiss(comment)

    def on_input_submitted(self, event: widgets.Input.Submitted) -> None:
        self.dismiss(event.value)


class ConfirmModal(screen.ModalScreen[bool]):
    """A generic confirmation modal."""

    def __init__(
        self,
        title: str,
        message: str,
        confirm_label: str = "Confirm",
        cancel_label: str = "Cancel",
        variant: Literal["primary", "error"] = "primary",
    ) -> None:
        super().__init__()
        self.title_text = title
        self.message_text = message
        self.confirm_label = confirm_label
        self.cancel_label = cancel_label
        self.variant: Literal["primary", "error"] = variant

    def compose(self) -> app.ComposeResult:
        with containers.Vertical(id="dialog"):
            yield widgets.Label(self.title_text, id="dialog-title")
            yield widgets.Static(self.message_text, id="dialog-message")
            with containers.Horizontal(id="dialog-buttons"):
                yield widgets.Button(self.cancel_label, variant="error", id="cancel")
                yield widgets.Button(
                    self.confirm_label, variant=self.variant, id="confirm"
                )

    def on_button_pressed(self, event: widgets.Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)


class RollbackPreviewModal(screen.ModalScreen[bool]):
    """A modal for previewing a rollback script."""

    def __init__(self, script_text: str) -> None:
        super().__init__()
        self.script_text = script_text

    def compose(self) -> app.ComposeResult:
        with containers.Vertical(id="rollback-dialog"):
            yield widgets.Label("Rollback Preview", id="dialog-title")
            yield widgets.Label(
                "Please review the rollback script below before execution."
            )
            yield widgets.TextArea(
                self.script_text, read_only=True, id="rollback-script"
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
