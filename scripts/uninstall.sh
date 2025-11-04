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

set -uexo pipefail

readonly MY_PATH=$(cd $(dirname "$0") && pwd)

cd $MY_PATH/..

rm -f /usr/share/libalpm/hooks/05-yabsnap-pacman-pre.hook

systemctl disable yabsnap.timer || true
systemctl daemon-reload

# TODO: Remove the following two lines after sufficient time has passed.
# Prior to 2022-10-12, /etc/systemd/system was used.
rm -f /etc/systemd/system/yabsnap.service
rm -f /etc/systemd/system/yabsnap.timer

rm -f /usr/lib/systemd/system/yabsnap.service
rm -f /usr/lib/systemd/system/yabsnap.timer

rm -f /usr/bin/yabsnap
rm -rf /usr/share/yabsnap 2> /dev/null

rm -f /usr/share/bash-completion/completions/yabsnap
rm -f /usr/share/zsh/site-functions/_yabsnap
rm -f /usr/share/man/man1/yabsnap.1.gz
