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

readonly MY_PATH=$(cd $(dirname "$0") && pwd)

cd ${MY_PATH}

black --check code/

pyright code/

# flake8 --ignore=E203,E501,W503 code/

mypy --ignore-missing-imports --show-column-numbers --check-untyped-defs --show-error-codes code/

python -m unittest discover -s . -p '*_test.py'

