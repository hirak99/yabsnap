import datetime
import json
import os
import subprocess

from textual import app
from textual import binding
from textual import containers
from textual import events
from textual import widgets

from .. import configs
from ..snapshot_logic import rollbacker
from ..snapshot_logic import snap_holder
from ..snapshot_logic import snap_operator
from ..utils import human_interval
from . import keypress_overlay
from . import screens
from . import widgets as tui_widgets

from typing import ClassVar


class _YabsnapApp(app.App[None]):
    """The main TUI application for yabsnap."""

    CSS = (
        """
    Screen {
        layout: horizontal;
        layers: base overlay;
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

    #json-display {
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
        + keypress_overlay.CSS
    )

    BINDINGS: ClassVar[list[binding.BindingType]] = [
        binding.Binding("q", "quit", "Quit", show=True),
        binding.Binding("c", "create_snapshot", "Create", show=True),
        binding.Binding("d", "delete_snapshot", "Delete", show=True),
        binding.Binding("r", "rollback", "Rollback", show=True),
        binding.Binding("t", "open_terminal", "Terminal", show=True),
        binding.Binding("m", "view_metadata", "Metadata", show=True),
        binding.Binding("f5", "refresh_data", "Refresh", show=True),
    ]

    def __init__(
        self, source_filter: str | None = None, show_keys: bool = False
    ) -> None:
        super().__init__()
        self._source_filter: str | None = source_filter
        self._show_keys: bool = show_keys
        self._current_config: configs.Config | None = None

    def compose(self) -> app.ComposeResult:
        # Drop the window title bar by commenting out Header.
        # yield widgets.Header()
        with containers.Horizontal():
            with containers.Vertical(id="sidebar"):
                yield widgets.Label("Configurations", id="sidebar-header")
                yield widgets.ListView(id="config-list")
            with containers.Vertical(id="main-content"):
                yield widgets.DataTable(id="snapshot-table")
        yield widgets.Footer()
        if self._show_keys:
            yield keypress_overlay.KeyPressOverlay(id="keypress-overlay")

    def on_key(self, event: events.Key) -> None:
        keypress_overlay.handle_key(self, event)

    def on_mount(self) -> None:
        self._load_configs()
        table: widgets.DataTable[str] = self.query_one(
            "#snapshot-table", widgets.DataTable
        )
        table.add_columns("Timestamp", "Type", "Age", "TTL", "Comment")
        table.cursor_type = "row"

    def _load_configs(self) -> None:
        config_list: widgets.ListView = self.query_one("#config-list", widgets.ListView)
        config_list.clear()
        for config in configs.iterate_configs(self._source_filter):
            config_list.append(tui_widgets.ConfigItem(config))

        if config_list.children:
            config_list.index = 0

    def on_list_view_highlighted(self, event: widgets.ListView.Highlighted) -> None:
        if isinstance(event.item, tui_widgets.ConfigItem):
            self._current_config = event.item.config
            self._refresh_snapshots()

    def _refresh_snapshots(self) -> None:
        if not self._current_config:
            return

        table: widgets.DataTable[str] = self.query_one(
            "#snapshot-table", widgets.DataTable
        )
        table.clear()

        now: datetime.datetime = datetime.datetime.now()
        for snap in snap_operator.get_existing_snaps(self._current_config):
            # Format trigger SIU
            trigger_str: str = "".join(
                c if snap.metadata.trigger == c else "-" for c in "SIU"
            )

            # Age
            elapsed: float = (now - snap.snaptime).total_seconds()
            age_str: str = human_interval.humanize(elapsed)

            # TTL
            ttl_str: str = ""
            if snap.metadata.expiry is not None:
                ttl: float = snap.metadata.expiry - now.timestamp()
                ttl_str = human_interval.humanize(ttl)

            table.add_row(
                snap.snaptime.strftime("%Y-%m-%d %H:%M:%S"),
                trigger_str,
                age_str,
                ttl_str,
                snap.metadata.comment,
                key=snap.target,
            )

    def action_refresh_data(self) -> None:
        self._refresh_snapshots()

    def action_create_snapshot(self) -> None:
        if not self._current_config:
            self.notify("No configuration selected", severity="warning")
            return

        def on_modal_result(comment: str | None) -> None:
            if comment is None:
                self.notify("No comment was provided, aborted.", severity="information")
                return

            assert self._current_config is not None
            try:
                now: datetime.datetime = datetime.datetime.now()
                snapper: snap_operator.SnapOperator = snap_operator.SnapOperator(
                    self._current_config, now
                )
                snapper.create(comment)
                self.notify(f"Snapshot created for {self._current_config.source}")
                self._refresh_snapshots()
            except PermissionError:
                self.notify("Permission denied. Run as root?", severity="error")
            except Exception as e:
                self.notify(f"Error: {e!s}", severity="error")

        self.push_screen(screens.CreateModal(), on_modal_result)

    def action_delete_snapshot(self) -> None:
        if not self._current_config:
            return

        table: widgets.DataTable[str] = self.query_one(
            "#snapshot-table", widgets.DataTable
        )

        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        target_path: str = str(row_key.value)

        def on_confirm(confirmed: bool | None) -> None:
            if not confirmed:
                return
            try:
                assert self._current_config is not None
                snap: snap_holder.Snapshot = snap_holder.Snapshot(target_path)
                snap.delete()
                self._current_config.call_post_hooks()
                self.notify(f"Deleted snapshot: {target_path}")
                self._refresh_snapshots()
            except PermissionError:
                self.notify("Permission denied. Run as root?", severity="error")
            except Exception as e:
                self.notify(f"Error deleting snapshot: {e!s}", severity="error")

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
        if not self._current_config:
            return

        table: widgets.DataTable[str] = self.query_one(
            "#snapshot-table", widgets.DataTable
        )

        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        target_path: str = str(row_key.value)

        script_text: str | None = rollbacker.get_rollback_script_text(
            [self._current_config], target_path, subvol_map=None
        )

        if not script_text:
            self.notify("Could not generate rollback script", severity="error")
            return

        def on_confirm(confirmed: bool | None) -> None:
            if not confirmed:
                return None
            try:
                # Suspend TUI to run the script.
                with self.suspend():
                    rollbacker.save_and_execute_script(script_text)
                self.notify("Rollback script executed successfully.")
            except subprocess.CalledProcessError as e:
                self.notify(f"Rollback execution failed: {e!s}", severity="error")
            except Exception as e:
                self.notify(f"An unexpected error occurred: {e!s}", severity="error")

        self.push_screen(screens.RollbackPreviewModal(script_text), on_confirm)

    def action_view_metadata(self) -> None:
        if not self._current_config:
            return

        table: widgets.DataTable[str] = self.query_one(
            "#snapshot-table", widgets.DataTable
        )

        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            target_path: str = str(row_key.value)
        except Exception:
            self.notify("No snapshot selected", severity="warning")
            return

        try:
            snap: snap_holder.Snapshot = snap_holder.Snapshot(target_path)
            # Combine common info with snap-specific metadata
            metadata_dict = {
                "config_file": self._current_config.config_file,
                "source": self._current_config.source,
                "target": target_path,
            }
            metadata_dict.update(snap.metadata.as_json())
            json_text = json.dumps(metadata_dict, indent=2)
            self.push_screen(screens.ShowJsonModal("Snapshot Metadata", json_text))
        except Exception as e:
            self.notify(f"Error loading metadata: {e!s}", severity="error")

    def action_open_terminal(self) -> None:
        if not self._current_config:
            return

        table: widgets.DataTable[str] = self.query_one(
            "#snapshot-table", widgets.DataTable
        )

        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            target_path: str = str(row_key.value)
        except Exception:
            self.notify("No snapshot selected", severity="warning")
            return

        if not os.path.isdir(target_path):
            self.notify(f"Directory does not exist: {target_path}", severity="error")
            return

        shell = os.environ.get("SHELL", "/bin/bash")
        with self.suspend():
            print()
            print(f"Opening terminal in {target_path}")
            print("Type 'exit' or press Ctrl+D to return to yabsnap.")
            subprocess.run([shell], cwd=target_path)


def run(source_filter: str | None = None, show_keys: bool = False) -> None:
    """Entry point for the TUI application."""
    yabsnap_app: _YabsnapApp = _YabsnapApp(source_filter, show_keys)
    yabsnap_app.run()
