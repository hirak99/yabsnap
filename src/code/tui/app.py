import datetime
import subprocess

from textual import app
from textual import binding
from textual import containers
from textual import widgets

from . import screens
from . import widgets as tui_widgets
from .. import configs
from ..snapshot_logic import rollbacker
from ..snapshot_logic import snap_operator
from ..utils import human_interval


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
        max-height: 80%;
        border: thick $primary;
        background: $surface;
        align: center middle;
    }

    #dialog-message {
        height: auto;
        max-height: 10;
        overflow-y: auto;
        margin-bottom: 1;
    }

    #rollback-dialog {
        padding: 1 2;
        width: 90%;
        height: 90%;
        border: thick $primary;
        background: $surface;
        align: center middle;
    }

    #rollback-script {
        margin-top: 1;
        height: 1fr;
        border: solid $primary;
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
            with tui_widgets.VerticalSidebar(id="sidebar"):
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
            config_list.append(tui_widgets.ConfigItem(config))

        if config_list.children:
            config_list.index = 0

    def on_list_view_highlighted(self, event: widgets.ListView.Highlighted) -> None:
        if isinstance(event.item, tui_widgets.ConfigItem):
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

        self.push_screen(screens.CreateModal(), on_modal_result)

    def action_delete_snapshot(self) -> None:
        if not self.current_config:
            return

        table = self.query_one("#snapshot-table", widgets.DataTable)
        if table.cursor_row is None:
            self.notify("No snapshot selected", severity="error")
            return

        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        target_path = str(row_key.value)

        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                try:
                    from ..snapshot_logic import snap_holder

                    snap = snap_holder.Snapshot(target_path)
                    snap.delete()
                    self.current_config.call_post_hooks()
                    self.notify(f"Deleted snapshot: {target_path}")
                    self.refresh_snapshots()
                except Exception as e:
                    self.notify(f"Error deleting snapshot: {str(e)}", severity="error")

        self.push_screen(
            screens.ConfirmModal(
                "Delete Snapshot",
                f"Are you sure you want to delete {target_path}?",
                confirm_label="Delete",
                variant="error",
            ),
            on_confirm,
        )

    def action_rollback(self) -> None:
        if not self.current_config:
            return

        table = self.query_one("#snapshot-table", widgets.DataTable)
        if table.cursor_row is None:
            self.notify("No snapshot selected", severity="error")
            return

        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        target_path = str(row_key.value)
        # Using a single config for generation here.
        script_text = rollbacker._get_rollback_script_text(
            [self.current_config], target_path, subvol_map=None
        )

        if not script_text:
            self.notify("Could not generate rollback script", variant="error")
            return

        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                try:
                    # Suspend TUI to run the script.
                    with self.suspend():
                        rollbacker._save_and_execute_script(script_text)
                    self.notify("Rollback script executed successfully.")
                except subprocess.CalledProcessError as e:
                    self.notify(f"Rollback execution failed: {str(e)}", variant="error")
                except Exception as e:
                    self.notify(
                        f"An unexpected error occurred: {str(e)}", variant="error"
                    )

        self.push_screen(screens.RollbackPreviewModal(script_text), on_confirm)


def run(source_filter: str | None = None):
    yabsnap_app = YabsnapApp(source_filter)
    yabsnap_app.run()
