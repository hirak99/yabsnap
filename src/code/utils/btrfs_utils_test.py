import unittest

from . import btrfs_utils

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false

# Commands like below can be used to generate test case -
# # truncate -s 1G test_btrfs.img
# # mount mount_dir test_btrfs.img mount
# # btrfs subv create mount_dir/@
# # sudo mount -o remount,subvol=@ mount_dir  # Switch to @
# # cd mount_dir
# # btrfs subv create @B
# # btrfs subv create @B/C
# # touch @B/C/test_file
# # # Simulate a scheduled snapshot.
# # btrfs subv snap -r @B @B2
# # # Simulate rollback to a state before nested subv.
# # mv @B @B_old
# # btrfs subv snap @B2 @B
# # # The subv C is also present in @B.
# # ls @B/C

# Paths shown when `btrfs subv list .` is invoked from mounted "@".
_TEST_SUBVOLS = """ID 279 gen 60 top level 285 path @B_old
ID 280 gen 52 top level 279 path @B_old/C
ID 282 gen 58 top level 285 path @B
ID 283 gen 52 top level 280 path @B_old/C/D
ID 284 gen 54 top level 282 path @B/E
ID 285 gen 61 top level 5 path @
ID 287 gen 60 top level 285 path a_dir/@B2"""


class TestBtrfsUtils(unittest.TestCase):
    def test_find_nested_subvs(self):
        subvols = btrfs_utils._parse_btrfs_list(_TEST_SUBVOLS)
        self.assertEqual(
            btrfs_utils._get_nested_subvs(subvols, 285),
            ["@B", "@B_old", "a_dir/@B2"],
        )
