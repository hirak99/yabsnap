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


set -ueo pipefail

readonly MY_PATH="$(dirname "$(realpath "$0")")"

cd $MY_PATH
# -u to enable unbuffered, to make sure `yabsnap ... 2>&1 | less` does not
# change order of logs.
# -O uses optimized code and ignores asserts. Also creates .opt-1.pyc instead of .pyc.
python3 -O -u -m code.main "$@"
