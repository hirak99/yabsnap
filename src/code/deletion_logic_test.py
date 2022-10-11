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

import datetime
import unittest

from . import deletion_logic


def _deleted_times(rules: dict[int, int], records: list[int]):
  mgr = deletion_logic.DeleteManager(
      {datetime.timedelta(seconds=k): v for k, v in rules.items()})
  nowts = 1664951765
  now = datetime.datetime.fromtimestamp(nowts)
  toscan = [(datetime.datetime.fromtimestamp(nowts + x), str(x)) for x in records]
  return [
      int(0.5 + x.timestamp()) - nowts for x, _ in mgr.get_deletes(now, toscan)
  ]


class TestDeletionLogic(unittest.TestCase):

  def test_checks(self):
    with self.assertRaisesRegex(ValueError, 'not in order'):
      self.assertEqual(_deleted_times({100: 1}, [-115, -210, -5]), [-210, -115])
    with self.assertRaisesRegex(ValueError, 'in the future'):
      self.assertEqual(_deleted_times({100: 1}, [-115, 5]), [-210, -115])

  def test_single_rule(self):
    self.assertEqual(_deleted_times({100: 1}, [-210, -115, -5]), [-210, -115])
    self.assertEqual(_deleted_times({100: 1}, [-115, -111, -5]), [-115, -111])
    self.assertEqual(_deleted_times({100: 1}, [-115, -15, -5]), [-115, -5])

    self.assertEqual(_deleted_times({100: 2}, [-210, -115, -5]), [-210])
    self.assertEqual(_deleted_times({100: 2}, [-115, -111, -5]), [-111])
    self.assertEqual(_deleted_times({100: 2}, [-115, -15, -5]), [-5])

  def test_multi_rule(self):
    self.assertEqual(_deleted_times({100: 0, 10: 0}, [-115, -105, -25, -15, -5]), [-115, -105, -25, -15, -5])
    self.assertEqual(_deleted_times({100: 0, 10: 2}, [-115, -105, -25, -15, -5]), [-115, -105, -25])
    self.assertEqual(_deleted_times({100: 0, 10: 3}, [-115, -105, -25, -15, -5]), [-115, -105])
    self.assertEqual(_deleted_times({100: 0, 10: 4}, [-115, -105, -25, -15, -5]), [-115, -105])
    self.assertEqual(_deleted_times({100: 0, 10: 40}, [-115, -105, -25, -15, -5]), [])

    self.assertEqual(_deleted_times({100: 2, 10: 0}, [-115, -25, -15, -5]), [-15, -5])
    self.assertEqual(_deleted_times({100: 2, 10: 1}, [-115, -25, -15, -5]), [-15])
    self.assertEqual(_deleted_times({100: 2, 10: 2}, [-115, -25, -15, -5]), [])
    self.assertEqual(_deleted_times({100: 2, 10: 4}, [-115, -25, -15, -5]), [])


if __name__ == '__main__':
  unittest.main()
