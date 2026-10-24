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
from ..snapshot_logic import snap_holder
from ..snapshot_logic import snap_operator
from ..utils import human_interval
from ..utils import time_lock
from . import keypress_overlay
from . import rollback_flow
from . import screens
from . import widgets as tui_widgets

from typing import ClassVar


def _snapshot_row(
    snap: snap_holder.Snapshot, now: datetime.datetime
) -> tuple[str, str, str, str, str]:
    """Formats `snap` as a table row: timestamp, trigger, age, TTL, comment."""
    # The trigger is a single character (S/I/U, or "" for unknown); show it as a
    # flag, e.g. "--U" for a user snapshot.
    trigger_str: str = "".join(c if snap.metadata.trigger == c else "-" for c in "SIU")

    age_str: str = human_interval.humanize((now - snap.snaptime).total_seconds())

    ttl_str: str = ""
    if snap.metadata.expiry is not None:
        ttl_str = human_interval.humanize(snap.metadata.expiry - now.timestamp())

    return (
        snap.snaptime.strftime("%Y-%m-%d %H:%M:%S"),
        trigger_str,
        age_str,
        ttl_str,
        snap.metadata.comment,
    )


class _YabsnapApp(app.App[None]):
    """The main TUI application for yabsnap."""

    # App chrome lives in app.tcss; modal styling lives next to the modals, in
    # screens.tcss.
    CSS_PATH = "app.tcss"

    # Loaded after CSS_PATH.
    CSS = keypress_overlay.CSS

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
        self._rollback_flow: rollback_flow.RollbackFlow = rollback_flow.RollbackFlow(
            self
        )

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
            table.add_row(*_snapshot_row(snap, now), key=snap.target)

    def _selected_target(self) -> str | None:
        """The target path of the snapshot under the cursor, if there is one.

        Notifies the user when no snapshot is selected, since every action that
        operates on a single snapshot needs the same check.
        """
        table: widgets.DataTable[str] = self.query_one(
            "#snapshot-table", widgets.DataTable
        )
        if table.row_count == 0:
            self.notify("No snapshot selected", severity="warning")
            return None
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        return str(row_key.value)

    def action_refresh_data(self) -> None:
        self._refresh_snapshots()

    def action_quit(self) -> None:
        if self._rollback_flow.is_running:
            self.notify(
                "Rollback in progress; please wait for it to finish.",
                severity="warning",
            )
            return
        self.exit()

    def action_create_snapshot(self) -> None:
        if not self._current_config:
            self.notify("No configuration selected", severity="warning")
            return
        if self._rollback_flow.is_running:
            self.notify("Rollback in progress; please wait.", severity="warning")
            return

        def on_modal_result(comment: str | None) -> None:
            if comment is None:
                self.notify("No comment was provided, aborted.", severity="information")
                return

            assert self._current_config is not None
            try:
                with time_lock.locked_now() as now:
                    snapper: snap_operator.SnapOperator = snap_operator.SnapOperator(
                        self._current_config, now
                    )
                    snapper.create(comment)
                self._current_config.call_post_hooks()
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
        if self._rollback_flow.is_running:
            self.notify("Rollback in progress; please wait.", severity="warning")
            return

        target_path: str | None = self._selected_target()
        if target_path is None:
            return

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
        if self._rollback_flow.is_running:
            self.notify("Rollback already in progress.", severity="warning")
            return

        target_path: str | None = self._selected_target()
        self._rollback_flow.request(self._current_config, target_path)

    def action_view_metadata(self) -> None:
        if not self._current_config:
            return

        target_path: str | None = self._selected_target()
        if target_path is None:
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

        target_path: str | None = self._selected_target()
        if target_path is None:
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
