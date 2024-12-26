import contextlib
import datetime
import pathlib
from typing import Any, Protocol, Iterator

from . import configs
from . import global_flags
from . import human_interval
from . import snap_holder


_filters: dict[str, type["SnapshotFilterProtocol"]] = {}


def get_filters(args: dict[str, Any]) -> Iterator["SnapshotFilterProtocol"]:
    for arg_name, arg_value in args.items():
        if arg_name in _filters:
            yield _filters[arg_name](arg_value)


def _register_filter(cls: type["SnapshotFilterProtocol"]):
    for name in cls.arg_name_set:
        _filters[name] = cls


class SnapshotFilterProtocol(Protocol):
    arg_name_set: tuple[str, ...]

    def __init__(self, status: Any): ...

    def _filter(self, snap: snap_holder.Snapshot) -> bool: ...

    def __call__(self, *args, **kwargs):
        return self._filter(*args, **kwargs)


@_register_filter
class IndicatorFilter(SnapshotFilterProtocol):
    arg_name_set = ("indicator",)

    def __init__(self, indicator: str):
        self._available = True
        if not indicator:
            self._available = False

        self._indicator = indicator.upper()

    def _filter(self, snap: snap_holder.Snapshot) -> bool:
        return snap.metadata.trigger == self._indicator

    def __call__(self, *args, **kwargs):
        if self._available is False:
            return False
        return self._filter(*args, **kwargs)


@_register_filter
class TimeScopeFilter(SnapshotFilterProtocol):
    arg_name_set = ("start", "end")

    def __init__(self, start_date_string: str = "", end_date_string: str = ""):
        self._available = True
        if not (start_date_string and end_date_string):
            self._available = False

        self._start_datetime = (
            datetime.datetime.strptime(start_date_string, global_flags.TIME_FORMAT)
            if start_date_string
            else datetime.datetime.min
        )
        self._end_datetime = (
            datetime.datetime.strptime(end_date_string, global_flags.TIME_FORMAT)
            if end_date_string
            else datetime.datetime.max
        )

    def _filter(self, snap: snap_holder.Snapshot) -> bool:
        return self._start_datetime <= snap.snaptime < self._end_datetime

    def __call__(self, *args, **kwargs):
        if self._available is False:
            return False
        return self._filter(*args, **kwargs)


def apply_snapshot_filters(
    snaps_of_config: dict[configs.Config, list[snap_holder.Snapshot]],
    *filters: SnapshotFilterProtocol,
) -> dict[configs.Config, list[snap_holder.Snapshot]]:
    """Use the filter to select the snapshots\
       that actually need to be processed for each configuration."""
    filted_mapping: dict[configs.Config, list[snap_holder.Snapshot]]
    filted_mapping = {config: [] for config in snaps_of_config}

    for config, snaps in snaps_of_config.items():
        filted_snaps_set = set(snaps)
        filted_snaps_set.intersection_update(filter(func, snaps) for func in filters)

        filted_mapping[config] = sorted(
            filted_snaps_set, key=lambda snap: snap.snaptime
        )
    return filted_mapping


def list_snapshots(snaps_of_config: dict[configs.Config, list[snap_holder.Snapshot]]):
    now = datetime.datetime.now()

    for config, snaps in snaps_of_config.items():
        config_abs_path = pathlib.Path(config.config_file).resolve()
        print(f"Config: {str(config_abs_path)} (source={config.source})")
        print(f"Snaps at: {config.dest_prefix}...")

        for snap in snaps:
            columns = []
            snap_timestamp = snap.snaptime.strftime(global_flags.TIME_FORMAT)
            columns.append(f"  {snap_timestamp}")

            trigger_str = "".join(
                c if snap.metadata.trigger == c else " " for c in "SIU"
            )
            columns.append(trigger_str)

            elapsed = (now - snap.snaptime).total_seconds()
            elapsed_str = f"({human_interval.humanize(elapsed)} ago)"
            columns.append(f"{elapsed_str:<20}")
            columns.append(snap.metadata.comment)

            print("  ".join(columns))
        print()


def confirm_deletion_snapshots() -> bool:
    confirm = input("Are you sure you want to delete the above snapshots?  [y/N]")
    match confirm:
        case "y" | "Y" | "yes" | "Yes" | "YES":
            return True
        case _:
            return False


def iso8601_to_timestamp_string(suffix: str) -> str:
    """Convert an ISO 8601 compliant string to a timestamp string"""
    with contextlib.suppress(ValueError):
        dt = datetime.datetime.strptime(suffix, global_flags.TIME_FORMAT)
        return suffix

    try:
        dt = datetime.datetime.fromisoformat(suffix)
    except ValueError:
        raise ValueError(
            "Suffix only accepts the following formats:\n"
            "  1. %Y%m%d%H%M%S (e.g. 20241101201015)\n"
            "  2. ISO 8601 compliant timestamp string (e.g. 2024-11-01_20:10:15)"
        )
    else:
        return dt.strftime(global_flags.TIME_FORMAT)  # %Y%m%d%H%M%S
