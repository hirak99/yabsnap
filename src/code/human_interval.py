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
"""Basic parser for human intervals.
Matches convention established in `man systemd.time`.
E.g. parse_to_secs('10 hr')  # Returns 36000.
"""
import re

from typing import Optional

# String units to seconds.
# Matches convention given in `man systemd.time`.
_MAPPINGS_SYNONYMS = {
    ('usec', 'us', 'µs'): 1e-6,
    ('msec', 'ms'): 1e-3,
    ('seconds', 'second', 'sec', 's'): 1,
    ('minutes', 'minute', 'min', 'm'): 60,
    ('hours', 'hour', 'hr', 'h'): 60 * 60,
    ('days', 'day', 'd'): 24 * 60 * 60,
    ('weeks', 'week', 'w'): 7 * 24 * 60 * 60,
    ('months', 'month', 'M'): 30.44 * 24 * 60 * 60,
    ('years', 'year', 'y'): 365.24 * 24 * 60 * 60,
}

# Unroll the tuples from _MAPPINGS_SYSTEMD.
_MAPPINGS = {k: v for (t, v) in _MAPPINGS_SYNONYMS.items() for k in t}


def parse_to_secs(human_interval: str) -> float:
  units = '|'.join(sorted(_MAPPINGS))
  m = re.match(rf'^\s*(?P<value>[0-9]*\.?[0-9]*)\s*(?P<unit>{units})\s*$',
               human_interval)
  if not m:
    known_suffixes = ','.join(sorted(_MAPPINGS))
    raise ValueError(
        f'Could not parse {human_interval} as a time interval. '
        f'Expected <num><suffix> where <suffix> is one of {known_suffixes}.')
  return float(m.group('value')) * _MAPPINGS[m.group('unit')]


# String suffix to use for timestamp.
_SUFFIXES = [
    (365.24 * 24 * 60 * 60, 'year'),
    (30 * 24 * 60 * 60, 'month'),
    (7 * 24 * 60 * 60, 'week'),
    (24 * 60 * 60, 'day'),
    (60 * 60, 'h'),
    (60, 'm'),
    (1, 's'),
]

_ACCURACY = 0.01


def humanize(seconds: int | float) -> str:
  result: list[str] = []
  largest_duration: Optional[float] = None
  for duration, suffix in _SUFFIXES:
    if seconds >= duration:
      count, seconds = divmod(seconds, duration)
      if largest_duration is None:
        largest_duration = duration
      elif duration < largest_duration * _ACCURACY:
        break
      if count == 0:
        continue
      if len(suffix) > 1:
        pluralize = 's' if count > 1 else ''
        result.append(f'{count:0.0f} {suffix}{pluralize}')
      else:
        result.append(f'{count:0.0f}{suffix}')
  return ' '.join(result)
