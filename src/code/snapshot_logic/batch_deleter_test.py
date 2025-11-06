import datetime
import itertools
import unittest

from . import batch_deleter
from . import snap_holder
from .. import configs
from .. import global_flags

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false


class TestParseISO8601Datetime(unittest.TestCase):
    def test_valid_datetime_format(self):
        datetime_strings: list[datetime.datetime] = [
            batch_deleter._parse_iso8601_datetime(datetime_string)
            for datetime_string in [
                "20241101201015",
                "2024-11-01-201015",
                "2024-11-01 20:10:15",
                "2024-11-01_20:10:15",
                "2024-11-01 20:10",
            ]
        ]
        excepted_results: list[datetime.datetime] = [
            datetime.datetime.strptime(datetime_string, global_flags.TIME_FORMAT)
            for datetime_string in [
                "20241101201015",
                "20241101201015",
                "20241101201015",
                "20241101201015",
                "20241101201000",
            ]
        ]

        self.assertEqual(datetime_strings, excepted_results)

    def test_invalid_datetime_format(self):
        datetime_strings = [
            "2024-11-01 20-10-15",
            "2024_11_01 20:10:15",
            "2024/11/01 20:10:15",
            # The intuitive expected value is 2024-11-01 20:10:00,
            # but due to the length being less than 14 digits (it is only 12 digits here),
            # there could be ambiguity; the actual value is 2024-11-01 20:01:00.
            "2024" + "1101" + "2010",
        ]

        for datetime_string in datetime_strings:
            with self.subTest(datetime_string=datetime_string):
                with self.assertRaises(ValueError):
                    batch_deleter._parse_iso8601_datetime(datetime_string)


class TestRegisterFilter(unittest.TestCase):
    class NothingFilter(batch_deleter._SnapshotFilterProtocol):
        arg_name_set = ("test",)

        def __init__(self, take_none: None): ...

        def __call__(self, snap: snap_holder.Snapshot) -> bool:
            return False

    def test_register(self):
        batch_deleter._register_filter(self.NothingFilter)
        nothing_filter_arg_name = self.NothingFilter.arg_name_set[-1]
        self.assertIn(nothing_filter_arg_name, batch_deleter._FILTERS)

        del batch_deleter._FILTERS["test"]

    def test_no_arg_name_set(self):
        del self.NothingFilter.arg_name_set

        with self.assertRaises(AttributeError):
            batch_deleter._register_filter(self.NothingFilter)
        self.NothingFilter.arg_name_set = ("test",)


class TestGetFilters(unittest.TestCase):
    def test_get_registed_filter(self):
        mininal_args = {
            "indicator": "S",
            "start": "2024" + "1101" + "201015",
            "end": "2024" + "1102" + "201000",
        }
        filters_list = list(batch_deleter.get_filters(mininal_args))
        self.assertEqual(len(filters_list), 3)

        self.assertEqual(
            getattr(filters_list[0], "_indicator"),
            mininal_args["indicator"],
        )
        self.assertEqual(
            getattr(filters_list[1], "_start_datetime"),
            datetime.datetime.strptime(mininal_args["start"], global_flags.TIME_FORMAT),
        )
        self.assertEqual(
            getattr(filters_list[2], "_end_datetime"),
            datetime.datetime.strptime(mininal_args["end"], global_flags.TIME_FORMAT),
        )

    def test_get_no_registed_filter(self):
        filter_iter = batch_deleter.get_filters({"test": None})
        with self.assertRaises(StopIteration):
            next(filter_iter)


class TestSnapshotFilters(unittest.TestCase):
    def setUp(self):
        self._config_snaps_mapping_list = [
            self._only_s_indicator_mapping(),  # 10 scheduled snapshots
            self._s_and_u_indicator_mapping(),  # 10 scheduled snapshots + 12 user snapshots
        ]

    def test_use_indicator_arg(self):
        user_snap_filter = next(batch_deleter.get_filters({"indicator": "U"}))
        filted_mapping = batch_deleter.apply_snapshot_filters(
            self._config_snaps_mapping_list, user_snap_filter
        )

        for mapping in filted_mapping:
            for snap in mapping.snaps:
                self.assertEqual(snap.metadata.trigger, "U")

        with self.assertRaises(StopIteration):
            # invalid indicator flag
            next(batch_deleter.get_filters({"indicator": None}))

    # Snapshots for testing, with creation times after November 2024.
    def test_use_start_arg_to_find_all_snaps(self):
        filter_iter = batch_deleter.get_filters({"start": "2024" + "1101" + "000015"})
        filted_mapping = batch_deleter.apply_snapshot_filters(
            self._config_snaps_mapping_list, *filter_iter
        )

        # Refer to the `setUp` function
        # the configuration file `s_and_u_config` has 10 scheduled snapshots and 2 user snapshots
        # while the configuration file `only_s_config` has 10 scheduled snapshots.
        snaps_total_number = sum(len(mapping.snaps) for mapping in filted_mapping)
        excepted_total_number = 10 + (10 + 2)  # 22 snapshots
        self.assertEqual(snaps_total_number, excepted_total_number)

    # The scheduled snapshots are created on or after November 10, 2024
    # while user snapshots were made before the 10th.
    # So, there are only 2 user snapshots before the 10th.
    def test_use_end_arg_to_find_two_snaps(self):
        filter_iter = batch_deleter.get_filters({"end": "2024" + "1109" + "053019"})
        filted_mapping = batch_deleter.apply_snapshot_filters(
            self._config_snaps_mapping_list, *filter_iter
        )

        snaps_total_number = sum(len(mapping.snaps) for mapping in filted_mapping)
        self.assertEqual(snaps_total_number, 2)

    # There are a total of 20 scheduled snapshots from `2024-11-11 07:05` to `2024-11-21 07:05`,
    # and 2 user snapshots from `2024-11-02 10:30:51` to `2024-11-03 17:21:30`.
    # Among the snapshots that meet the "scheduled" criteria, there are 20 in total.
    # After applying a time range filter, 4 of them fall within the period from `2024-11-01` to `2024-11-13`.
    def test_use_multi_args_find_two_snaps(self):
        mininal_args = {
            "indicator": "S",
            "start": "2024" + "1101" + "000015",
            "end": "2024" + "1113" + "000020",
        }
        filter_iter = batch_deleter.get_filters(mininal_args)
        filted_mapping = batch_deleter.apply_snapshot_filters(
            self._config_snaps_mapping_list, *filter_iter
        )

        snaps_total_number = sum(len(mapping.snaps) for mapping in filted_mapping)
        self.assertEqual(snaps_total_number, 4)

    # Create a test version of config_snapshots_mapping
    def _only_s_indicator_mapping(self) -> batch_deleter._ConfigSnapshotsRelation:
        config = configs.Config(
            config_file="config_in_only_s_path",
            source="to_be_backup_up_only_s_subvolume",
            dest_prefix="only_s-",
        )
        snaps = list(self._ten_indicator_s_snaps())
        return batch_deleter._ConfigSnapshotsRelation(config, snaps)

    def _s_and_u_indicator_mapping(self) -> batch_deleter._ConfigSnapshotsRelation:
        config = configs.Config(
            config_file="config_in_s_and_u_path",
            source="to_be_backup_up_s_and_u_subvolume",
            dest_prefix="s_and_u-",
        )
        snaps = list(
            itertools.chain(
                self._ten_indicator_s_snaps(), self._two_indicator_u_snaps()
            )
        )
        return batch_deleter._ConfigSnapshotsRelation(config, snaps)

    # Create a test version of snapshots
    def _ten_indicator_s_snaps(self) -> list[snap_holder.Snapshot]:
        snaps = [
            snap_holder.Snapshot("2024" + f"11{day}" + "070500")
            for day in range(11, 21)
        ]

        for snap in snaps:
            snap.metadata.trigger = "S"
        return snaps

    def _two_indicator_u_snaps(self) -> list[snap_holder.Snapshot]:
        snaps = [
            snap_holder.Snapshot("2024" + "1102" + "103051"),
            snap_holder.Snapshot("2024" + "1103" + "172130"),
        ]

        for snap in snaps:
            snap.metadata.trigger = "U"
        return snaps


if __name__ == "__main__":
    unittest.main()
