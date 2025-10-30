# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import tempfile
import unittest

from . import os_utils

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false


class OsUtilsTest(unittest.TestCase):
    def test_run_user_script(self):
        self.assertTrue(os_utils.run_user_script("true", []))
        self.assertTrue(os_utils.run_user_script("test", ["1", "=", "1"]))
        self.assertFalse(os_utils.run_user_script("test", ["1", "=", "2"]))
        with tempfile.TemporaryDirectory() as dir:
            # Script does not exist.
            self.assertFalse(os_utils.run_user_script(os.path.join(dir, "test.sh"), []))


if __name__ == "__main__":
    unittest.main()
