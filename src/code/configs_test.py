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

from . import configs

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false


class ConfigsTest(unittest.TestCase):
    def test_default_config(self):
        # Check that the bootstrap config indeed encodes defaults.
        config_file = str(configs._example_config_fname())
        config = configs.Config.from_configfile(config_file)
        expected_config = configs.Config(
            config_file=config_file, source="", dest_prefix=""
        )
        self.assertEqual(config, expected_config)

    def test_create_config(self):
        with tempfile.NamedTemporaryFile(prefix="yabsnap_config_test_") as file:
            configs.USER_CONFIG_FILE = file.name
            os.remove(file.name)
            # Create -
            configs.create_config("configname", "source")

            # Read back -
            read_config = configs.Config.from_configfile(file.name)
            self.assertEqual(read_config.source, "source")
            self.assertEqual(read_config.dest_prefix, "/.snapshots/@configname-")
            self.assertEqual(read_config.config_file, file.name)


if __name__ == "__main__":
    unittest.main()
