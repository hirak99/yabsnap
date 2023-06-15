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

readonly MY_PATH=$(cd $(dirname "$0") && pwd)

cd $MY_PATH/..

mkdir -p $PKGDIR/usr/share
rsync -aAXHSv src/ $PKGDIR/usr/share/yabsnap \
  --exclude '*_test.py' \
  --include '*/' --include '*.py' --include '*.sh' --include '*.conf' \
  --exclude '*' \
  --prune-empty-dirs \
  --delete
chmod -R g-w,a-w src/ $PKGDIR/usr/share/yabsnap
if $(which selinuxenabled 2>/dev/null); then
  restorecon -R src/ $PKGDIR/usr/share/yabsnap
fi

mkdir -p $PKGDIR/usr/bin
ln -sf /usr/share/yabsnap/yabsnap.sh $PKGDIR/usr/bin/yabsnap
chmod 755 $PKGDIR/usr/bin/yabsnap

mkdir -p $PKGDIR/usr/lib/systemd/system
install -Z artifacts/services/yabsnap.service $PKGDIR/usr/lib/systemd/system
install -Z artifacts/services/yabsnap.timer $PKGDIR/usr/lib/systemd/system
sudo systemctl daemon-reload

readonly HOOKDIR=/usr/share/libalpm/hooks/
if [[ -d "$HOOKDIR" ]]; then
  mkdir -p $PKGDIR/$HOOKDIR
  install -Z artifacts/pacman/05-yabsnap-pacman-pre.hook $PKGDIR/$HOOKDIR
else
  printf 'Not an Arch based distro, will not install hook.\n' >&2
fi

mkdir -p $PKGDIR/usr/share/man/man1
install artifacts/yabsnap.manpage $PKGDIR/usr/share/man/man1/yabsnap.1
