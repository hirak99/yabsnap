from textual import app
from textual import events
from textual import widgets

CSS = """
#keypress-overlay {
    display: none;
    layer: overlay;
    width: auto;
    height: auto;
    padding: 1 2;
    background: $accent;
    color: $text;
    text-style: bold;
    border: thick $primary;
    opacity: 0.8;
    offset-x: 4;
    offset-y: 85%;
}

#keypress-overlay.visible {
    display: block;
}
"""


class KeyPressOverlay(widgets.Static):
    """A transient overlay that shows key presses."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._active_keys: list[str] = []

    def show_key(self, key_name: str) -> None:
        self._active_keys.append(key_name)
        self._update_display()
        self.set_timer(1.0, lambda: self._remove_key(key_name))

    def _remove_key(self, key_name: str) -> None:
        if key_name in self._active_keys:
            self._active_keys.remove(key_name)
        self._update_display()

    def _update_display(self) -> None:
        if not self._active_keys:
            self.remove_class("visible")
        else:
            self.update(", ".join(self._active_keys))
            self.add_class("visible")


def handle_key(yabsnap_app: app.App[None], event: events.Key) -> None:
    """Handles key events for the keypress overlay."""
    if getattr(yabsnap_app, "_show_keys", False):
        try:
            overlay = yabsnap_app.query_one("#keypress-overlay", KeyPressOverlay)
            overlay.show_key(event.key.upper())
        except Exception:
            pass
