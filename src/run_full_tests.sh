#!/bin/bash
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

# Full tests, depends on mypy and flake8.

set -uexo pipefail

readonly MY_PATH=$(cd "$(dirname "$0")" && pwd)

cd "${MY_PATH}"

# This checks format, needs to be run separately from linting.
ruff format --check

# Linting.
ruff check . --select I

# Block auto-fixable lint issues.
ruff check . --fix --diff || { echo "Auto-fixable ruff issues found. Run: ruff check . --fix"; exit 1; }

# Type checking (pyright).
pyright code/

find . -type f -iname '*_test.py' -exec python -m unittest {} +
