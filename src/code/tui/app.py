import datetime
import os

from textual import app
from textual import binding
from textual import containers
from textual import screen
from textual import widgets

from .. import configs
from ..snapshot_logic import snap_operator
from ..utils import human_interval


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


class ConfigItem(widgets.ListItem):
    def __init__(self, config: configs.Config) -> None:
        super().__init__()
        self.config = config
        self.add_class("config-item")

    def compose(self) -> app.ComposeResult:
        yield widgets.Label(
            f"{os.path.basename(self.config.config_file)} ({self.config.source})"
        )


class YabsnapApp(app.App):
    CSS = """
    Screen {
        layout: horizontal;
    }

    #sidebar {
        width: 35;
        background: $panel;
        border-right: tall $primary;
    }

    #main-content {
        width: 1fr;
    }

    .config-item {
        padding: 0 1;
    }

    DataTable {
        height: 1fr;
    }

    #sidebar-header {
        padding: 1 2;
        background: $primary;
        color: $text;
        text-style: bold;
    }

    #dialog {
        padding: 1 2;
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        align: center middle;
    }

    #dialog-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #dialog-buttons {
        margin-top: 1;
        height: auto;
        align: right middle;
    }

    #dialog-buttons Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        binding.Binding("q", "quit", "Quit", show=True),
        binding.Binding("c", "create_snapshot", "Create", show=True),
        binding.Binding("d", "delete_snapshot", "Delete", show=True),
        binding.Binding("r", "rollback", "Rollback", show=True),
        binding.Binding("f5", "refresh_data", "Refresh", show=True),
    ]

    def __init__(self, source_filter: str | None = None) -> None:
        super().__init__()
        self.source_filter = source_filter
        self.current_config: configs.Config | None = None

    def compose(self) -> app.ComposeResult:
        yield widgets.Header()
        with containers.Horizontal():
            with VerticalSidebar(id="sidebar"):
                yield widgets.Label("Configurations", id="sidebar-header")
                yield widgets.ListView(id="config-list")
            with containers.Vertical(id="main-content"):
                yield widgets.DataTable(id="snapshot-table")
        yield widgets.Footer()

    def on_mount(self) -> None:
        self.load_configs()
        table = self.query_one("#snapshot-table", widgets.DataTable)
        table.add_columns("Timestamp", "Type", "Age", "TTL", "Comment")
        table.cursor_type = "row"

    def load_configs(self) -> None:
        config_list = self.query_one("#config-list", widgets.ListView)
        config_list.clear()
        for config in configs.iterate_configs(self.source_filter):
            config_list.append(ConfigItem(config))

        if config_list.children:
            config_list.index = 0

    def on_list_view_highlighted(self, event: widgets.ListView.Highlighted) -> None:
        if isinstance(event.item, ConfigItem):
            self.current_config = event.item.config
            self.refresh_snapshots()

    def refresh_snapshots(self) -> None:
        if not self.current_config:
            return

        table = self.query_one("#snapshot-table", widgets.DataTable)
        table.clear()

        now = datetime.datetime.now()
        for snap in snap_operator.get_existing_snaps(self.current_config):
            # Format trigger SIU
            trigger_str = "".join(
                c if snap.metadata.trigger == c else "-" for c in "SIU"
            )

            # Age
            elapsed = (now - snap.snaptime).total_seconds()
            age_str = human_interval.humanize(elapsed)

            # TTL
            ttl_str = ""
            if snap.metadata.expiry is not None:
                ttl = snap.metadata.expiry - now.timestamp()
                ttl_str = human_interval.humanize(ttl)

            table.add_row(
                snap.target.removeprefix(self.current_config.dest_prefix),
                trigger_str,
                age_str,
                ttl_str,
                snap.metadata.comment,
                key=snap.target,
            )

    def action_refresh_data(self) -> None:
        self.refresh_snapshots()

    def action_create_snapshot(self) -> None:
        if not self.current_config:
            self.notify("No configuration selected", variant="error")
            return

        def on_modal_result(comment: str | None) -> None:
            if comment is not None:
                try:
                    now = datetime.datetime.now()
                    snapper = snap_operator.SnapOperator(self.current_config, now)
                    snapper.create(comment)
                    self.notify(f"Snapshot created for {self.current_config.source}")
                    self.refresh_snapshots()
                except Exception as e:
                    self.notify(f"Error: {str(e)}", variant="error")

        self.push_screen(CreateModal(), on_modal_result)

    def action_delete_snapshot(self) -> None:
        self.notify("Delete snapshot triggered")

    def action_rollback(self) -> None:
        self.notify("Rollback triggered")


class VerticalSidebar(containers.Vertical):
    pass


def run(source_filter: str | None = None):
    yabsnap_app = YabsnapApp(source_filter)
    yabsnap_app.run()
