import os
import unittest

from . import rollbacker

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false


class TestCreateAndChmodScript(unittest.TestCase):
    def test_create_and_chmod(self):
        contents = [
            "This file is used for unit testing the yabsnap rollbacker module, generated from yabsnap."
        ]
        rollbacker._create_and_chmod_script(contents)
        self.assertTrue(os.path.exists(rollbacker._ROLLBACK_SCRIPT_FILEPATH))
        self.assertTrue(
            os.access(rollbacker._ROLLBACK_SCRIPT_FILEPATH, mode=os.X_OK)
        )

    def tearDown(self):
        os.remove(rollbacker._ROLLBACK_SCRIPT_FILEPATH)
