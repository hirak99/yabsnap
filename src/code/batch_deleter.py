import contextlib
import dataclasses
import datetime
import logging
import os
import pathlib

from . import configs
from . import global_flags
from . import human_interval
from . import snap_holder
from .mechanisms import snap_mechanisms

from typing import Any, Iterable, Iterator, Protocol

_FILTERS: dict[str, type["_SnapshotFilterProtocol"]] = {}


@dataclasses.dataclass(frozen=True)
class _ConfigSnapshotsRelation:
    config: configs.Config
    snaps: list[snap_holder.Snapshot]


def create_config_snapshots_mapping(
    configs_iter: Iterable[configs.Config],
) -> Iterator[_ConfigSnapshotsRelation]:
    """Create a configuration file and its associated snapshot relationship mapping."""
    for config in configs_iter:
        yield _ConfigSnapshotsRelation(config, list(_get_old_backups(config)))


# src/code/snap_operator.py has same function
def _get_old_backups(config: configs.Config) -> Iterator[snap_holder.Snapshot]:
    """Returns existing backups in chronological order."""
    destdir = os.path.dirname(config.dest_prefix)
    for fname in os.listdir(destdir):
        pathname = os.path.join(destdir, fname)
        if not os.path.isdir(pathname):
            continue
        if not pathname.startswith(config.dest_prefix):
            continue
        try:
            yield snap_holder.Snapshot(pathname)
        except ValueError:
            logging.warning(f"Could not parse timestamp, ignoring: {pathname}")


def get_filters(args: dict[str, Any]) -> Iterator["_SnapshotFilterProtocol"]:
    for arg_name, arg_value in args.items():
        if arg_name in _FILTERS and arg_value is not None:
            yield _FILTERS[arg_name](**{arg_name: arg_value})


def _register_filter(cls: type["_SnapshotFilterProtocol"]):
    for name in cls.arg_name_set:
        _FILTERS[name] = cls


class _SnapshotFilterProtocol(Protocol):
    arg_name_set: tuple[str, ...]

    def __init__(self, **kwargs): ...

    def __call__(self, snap: snap_holder.Snapshot) -> bool: ...


@_register_filter
class _IndicatorFilter(_SnapshotFilterProtocol):  # pyright: ignore[reportUnusedClass]
    arg_name_set = ("indicator",)

    def __init__(self, *, indicator: str):
        self._indicator = indicator.upper()
        logging.info(f"Added _IndicatorFilter: {self._indicator}")

    @property
    def indicator(self) -> str:
        return self._indicator

    def __call__(self, snap: snap_holder.Snapshot) -> bool:
        return snap.metadata.trigger == self._indicator


@_register_filter
class _TimeScopeFilter(_SnapshotFilterProtocol):  # pyright: ignore[reportUnusedClass]
    arg_name_set = ("start", "end")

    def __init__(self, *, start: str = "", end: str = ""):
        self._start_datetime = (
            datetime.datetime.strptime(start, global_flags.TIME_FORMAT)
            if start
            else datetime.datetime.min
        )
        self._end_datetime = (
            datetime.datetime.strptime(end, global_flags.TIME_FORMAT)
            if end
            else datetime.datetime.max
        )
        logging.info(
            f"Added _TimeScopeFilter: ({self._start_datetime}, {self._end_datetime})"
        )

    @property
    def start_datetime(self) -> datetime.datetime:
        return self._start_datetime

    @property
    def end_datetime(self) -> datetime.datetime:
        return self._end_datetime

    def __call__(self, snap: snap_holder.Snapshot) -> bool:
        return self._start_datetime <= snap.snaptime < self._end_datetime


def apply_snapshot_filters(
    config_snaps_mapping: Iterable[_ConfigSnapshotsRelation],
    *filters: _SnapshotFilterProtocol,
) -> Iterator[_ConfigSnapshotsRelation]:
    """Use the filter to select the snapshots\
       that actually need to be processed for each configuration."""
    for mapping in config_snaps_mapping:
        filtered_snaps: list[snap_holder.Snapshot] = []
        for snap in mapping.snaps:
            if all(func(snap) for func in filters):
                filtered_snaps.append(snap)

        yield _ConfigSnapshotsRelation(mapping.config, filtered_snaps)


def show_snapshots_to_be_deleted(
    config_snaps_mapping: Iterable[_ConfigSnapshotsRelation],
):
    banner = "=== THE SNAPSHOTS TO BE DELETED ==="
    print(banner)
    print()
    _list_snapshots(config_snaps_mapping)


def _list_snapshots(
    config_snaps_mapping: Iterable[_ConfigSnapshotsRelation],
):
    now = datetime.datetime.now()

    for mapping in config_snaps_mapping:
        if not mapping.snaps:
            # Skip displaying config with no matched snapshot to be deleted.
            continue
        config_abs_path = pathlib.Path(mapping.config.config_file).resolve()
        print(f"Config: {str(config_abs_path)} (source={mapping.config.source})")
        print(f"Snaps at: {mapping.config.dest_prefix}...")

        for snap in mapping.snaps:
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


def delete_snapshots(snaps: Iterable[snap_holder.Snapshot]):
    for snap in snaps:
        snap.delete()


def get_to_sync_list(configs: Iterable[configs.Config]) -> list[configs.Config]:
    return [
        config
        for config in configs
        if config.snap_type == snap_mechanisms.SnapType.BTRFS
    ]


def iso8601_to_timestamp_string(suffix: str) -> str:
    """Convert an ISO 8601 compliant datetime string to a timestamp string"""
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
        return dt.strftime(global_flags.TIME_FORMAT)
