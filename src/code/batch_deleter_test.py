import datetime
import itertools
import unittest

from . import batch_deleter
from . import configs
from . import global_flags
from . import snap_holder

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false


class TestISO8601ToTimestampString(unittest.TestCase):
    def test_support_timestamp_format(self):
        suffix_list = [
            "20241101201015",
            "2024-11-01 20:10:15",
            "2024-11-01_20:10:15",
            "2024-11-01 20:10",
        ]

        convert_results = map(batch_deleter.iso8601_to_timestamp_string, suffix_list)
        excepted_results = [
            "20241101201015",
            "20241101201015",
            "20241101201015",
            "20241101201000",
        ]
        self.assertEqual(list(convert_results), excepted_results)

    def test_unsupport_timestamp_format(self):
        suffix_list = [
            "2024/11/01",
            "2024/11/01 20:10",
            "2024/11/01 20:10:15",
            "2024/11/1_20:10:15",
            "11/01/2024",
        ]

        for suffix in suffix_list:
            with self.subTest(suffix=suffix):
                with self.assertRaises(ValueError):
                    batch_deleter.iso8601_to_timestamp_string(suffix)


class TestRegisterFilter(unittest.TestCase):
    class NothingFilter(batch_deleter.SnapshotFilterProtocol):
        arg_name_set = ("test",)

        def __init__(self, take_none: None): ...

        def _filter(self, snap: snap_holder.Snapshot) -> bool:
            return False

    def test_register(self):
        batch_deleter._register_filter(self.NothingFilter)
        nothing_filter_arg_name = self.NothingFilter.arg_name_set[-1]
        self.assertIn(nothing_filter_arg_name, batch_deleter._filters)

        del batch_deleter._filters["test"]

    def test_no_arg_name_set(self):
        del self.NothingFilter.arg_name_set

        with self.assertRaises(AttributeError):
            batch_deleter._register_filter(self.NothingFilter)
        self.NothingFilter.arg_name_set = ("test",)


class TestGetFilters(unittest.TestCase):
    def test_get_registed_filter(self):
        mininal_args = {
            "indicator": "S",
            "start": "202411012010",
            "end": "202411022010",
        }
        filters_iter = batch_deleter.get_filters(mininal_args)

        excepted_filters_attr_key = list(mininal_args.keys())
        excepted_filters_attr_value = [
            mininal_args["indicator"],
            datetime.datetime.strptime(mininal_args["start"], global_flags.TIME_FORMAT),
            datetime.datetime.strptime(mininal_args["end"], global_flags.TIME_FORMAT),
        ]

        for index, filter in enumerate(filters_iter):
            with self.subTest(filter=filter):
                self.assertEqual(
                    getattr(filter, excepted_filters_attr_key[index]),
                    excepted_filters_attr_value[index],
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
        filter_iter = batch_deleter.get_filters({"indicator": "U"})
        filted_mapping = batch_deleter.apply_snapshot_filters(
            self._config_snaps_mapping_list, *filter_iter
        )

        for mapping in filted_mapping:
            for snap in mapping.snaps:
                self.assertEqual(snap.metadata.trigger, "U")

    # Snapshots for testing, with creation times after November 2024.
    def test_use_start_arg_to_find_all_snaps(self):
        filter_iter = batch_deleter.get_filters({"start": "20241101" + "000000"})
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
        filter_iter = batch_deleter.get_filters({"end": "20241109" + "053019"})
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
            "start": "20241101" + "000000",
            "end": "20241113" + "000000",
        }
        filter_iter = batch_deleter.get_filters(mininal_args)
        filted_mapping = batch_deleter.apply_snapshot_filters(
            self._config_snaps_mapping_list, *filter_iter
        )

        snaps_total_number = sum(len(mapping.snaps) for mapping in filted_mapping)
        self.assertEqual(snaps_total_number, 4)

    # Create a test version of config_snapshots_mapping
    def _only_s_indicator_mapping(self) -> batch_deleter.ConfigSnapshotsRelation:
        config = configs.Config(
            config_file="config_in_only_s_path",
            source="to_be_backup_up_only_s_subvolume",
            dest_prefix="only_s-",
        )
        snaps = tuple(self._ten_indicator_s_snaps())
        return batch_deleter.ConfigSnapshotsRelation(config, snaps)

    def _s_and_u_indicator_mapping(self) -> batch_deleter.ConfigSnapshotsRelation:
        config = configs.Config(
            config_file="config_in_s_and_u_path",
            source="to_be_backup_up_s_and_u_subvolume",
            dest_prefix="s_and_u-",
        )
        snaps = tuple(
            itertools.chain(
                self._ten_indicator_s_snaps(), self._two_indicator_u_snaps()
            )
        )
        return batch_deleter.ConfigSnapshotsRelation(config, snaps)

    # Create a test version of snapshots
    def _ten_indicator_s_snaps(self) -> list[snap_holder.Snapshot]:
        snaps = [
            snap_holder.Snapshot(f"202411{day}" + "070500") for day in range(11, 21)
        ]

        for snap in snaps:
            snap.metadata.trigger = "S"
        return snaps

    def _two_indicator_u_snaps(self) -> list[snap_holder.Snapshot]:
        snaps = [
            snap_holder.Snapshot("20241102" + "103051"),
            snap_holder.Snapshot("20241103" + "172130"),
        ]

        for snap in snaps:
            snap.metadata.trigger = "U"
        return snaps


if __name__ == "__main__":
    unittest.main()
