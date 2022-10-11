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


set -uexo pipefail

# For AUR installation, everything must be done on a PKGDIR.
# The PKGDIR will be assumed to have the same structure as root.
readonly PKGDIR=${1-}

# Most of the installation will work on other distros;
# except pacman hook only works for Arch derived OS.
if [[ ! -f /usr/bin/pacman ]]; then
  echo Not Arch based distro, not proceeding. >&2
  exit 1
fi

readonly MY_PATH=$(cd $(dirname "$0") && pwd)

cd $MY_PATH/..

mkdir -p $PKGDIR/usr/share
rsync -aAXHSv src/ $PKGDIR/usr/share/yabsnap \
  --exclude '*_test.py' \
  --include '*/' --include '*.py' --include '*.sh' --include '*.conf' \
  --exclude '*' \
  --prune-empty-dirs \
  --delete
mkdir -p $PKGDIR/usr/bin
ln -sf /usr/share/yabsnap/yabsnap.sh $PKGDIR/usr/bin/yabsnap

mkdir -p $PKGDIR/usr/lib/systemd/system
cp artifacts/services/yabsnap.service $PKGDIR/usr/lib/systemd/system
cp artifacts/services/yabsnap.timer $PKGDIR/usr/lib/systemd/system

mkdir -p $PKGDIR/usr/share/libalpm/hooks/
cp artifacts/pacman/05-yabsnap-pacman-pre.hook $PKGDIR/usr/share/libalpm/hooks/

mkdir -p $PKGDIR/usr/share/man/man1
install artifacts/yabsnap.manpage $PKGDIR/usr/share/man/man1/yabsnap.1
