import os

from textual import app
from textual import widgets

from .. import configs


class ConfigItem(widgets.ListItem):
    """A list item representing a configuration."""

    def __init__(self, config: configs.Config) -> None:
        super().__init__()
        self.config: configs.Config = config
        self.add_class("config-item")

    def compose(self) -> app.ComposeResult:
        yield widgets.Label(
            f"{os.path.basename(self.config.config_file)} ({self.config.source})"
        )
