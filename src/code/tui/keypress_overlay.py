from textual import app
from textual import containers
from textual import events
from textual import widgets

CSS = """
#keypress-overlay {
    display: none;
    layer: overlay;
    width: auto;
    height: auto;
    offset-x: 4;
    offset-y: 85%;
}

#keypress-overlay.visible {
    display: block;
}

KeyBadge {
    width: auto;
    height: auto;
    padding: 0 1;

    background: $accent;
    color: $text;
    text-style: bold;

    border: thick $primary;
}
"""


class KeyBadge(widgets.Static):
    pass


class KeyPressOverlay(containers.Horizontal):
    """Shows each key press as an independent badge."""

    def show_key(self, key_name: str) -> None:
        badge = KeyBadge(key_name)
        self.mount(badge)

        # schedule removal of THIS specific instance
        self.set_timer(1.0, badge.remove)

        self.add_class("visible")

        # optional cleanup when empty
        self.set_timer(1.1, self._cleanup_visibility)

    def _cleanup_visibility(self) -> None:
        if not self.children:
            self.remove_class("visible")


def handle_key(yabsnap_app: app.App[None], event: events.Key) -> None:
    """Handles key events for the keypress overlay."""
    if getattr(yabsnap_app, "_show_keys", False):
        try:
            overlay = yabsnap_app.query_one("#keypress-overlay", KeyPressOverlay)
            overlay.show_key(event.key.upper())
        except Exception:
            pass
