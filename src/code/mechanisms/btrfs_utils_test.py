import unittest

from . import btrfs_utils

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false

_TEST_SUBVOLS = [
    btrfs_utils._Subvolume(id=279, gen=46, top_level=285, path="@/@B_old"),
    btrfs_utils._Subvolume(id=280, gen=52, top_level=279, path="@/@B_old/C"),
    btrfs_utils._Subvolume(id=282, gen=54, top_level=285, path="@/@B"),
    btrfs_utils._Subvolume(id=283, gen=52, top_level=280, path="@/@B_old/C/D"),
    btrfs_utils._Subvolume(id=284, gen=54, top_level=282, path="@/@B/E"),
    btrfs_utils._Subvolume(id=285, gen=56, top_level=5, path="@"),
    btrfs_utils._Subvolume(id=286, gen=56, top_level=285, path="@/@B2"),
]


class TestBtrfsUtils(unittest.TestCase):
    def test_find_nested_subvs(self):
        self.assertEqual(
            btrfs_utils._get_nested_subvs(_TEST_SUBVOLS, "@/@B_old"),
            ["C", "C/D"],
        )
        self.assertEqual(
            btrfs_utils._get_nested_subvs(_TEST_SUBVOLS, "@"),
            ["@B", "@B/E", "@B2", "@B_old", "@B_old/C", "@B_old/C/D"],
        )
        self.assertEqual(
            btrfs_utils._get_nested_subvs(_TEST_SUBVOLS, ""),
            ["@/@B", "@/@B/E", "@/@B2", "@/@B_old", "@/@B_old/C", "@/@B_old/C/D"],
        )
