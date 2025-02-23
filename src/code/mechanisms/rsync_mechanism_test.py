import unittest
from unittest import mock

from . import rsync_mechanism

from typing import Any

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false


class TestRsyncMechanism(unittest.TestCase):
    def setUp(self):
        self._patches: dict[str, Any] = {}
        self._patches["isdir"] = mock.patch("os.path.isdir", return_value=True)
        self._patches["execute"] = mock.patch.object(rsync_mechanism, "_execute_sh")
        self._patches["listdir"] = mock.patch("os.listdir", return_value=[])

        self._mocks: dict[str, mock.MagicMock] = {
            k: v.start() for k, v in self._patches.items()
        }

    def tearDown(self):
        all(x.stop() for x in self._patches.values())

    def test_invalid_destination_format(self):
        """Test if a ValueError is raised for an invalid destination format."""
        with self.assertRaises(ValueError):
            rsync_mechanism._initialize_destination("some/dir/invalid_destination")

        self._mocks["execute"].assert_not_called()
        self._mocks["listdir"].assert_not_called()

    def test_no_matching_snapshots(self):
        """Test when no matching snapshots are found."""
        self._mocks["listdir"].return_value = ["otherprefix20250223010101"]

        rsync_mechanism._initialize_destination("some/dir/prefix20250223010401")
        # Should not raise any error, and should return early without copying hardlinks.

        self._mocks["execute"].assert_not_called()
        self._mocks["listdir"].assert_called_once()

    def test_hardlink_command_execution(self):
        """Test if the hardlink command is executed correctly."""
        self._mocks["listdir"].return_value = [
            "prefix20250223010101",
            "prefix20250223010201",
        ]

        rsync_mechanism._initialize_destination("some/dir/prefix20250223010301")

        self._mocks["execute"].assert_called_with(
            "cp -al some/dir/prefix20250223010201/ some/dir/prefix20250223010301/"
        )


if __name__ == "__main__":
    unittest.main()
