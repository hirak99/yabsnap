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
rsync -rltXHSv src/ $PKGDIR/usr/share/yabsnap \
  --chown=root:root \
  --chmod=u=rwX,go=rX \
  --exclude '*_test.py' \
  --include '*/' --include '*.py' --include '*.sh' --include '*.conf' \
  --exclude '*' \
  --prune-empty-dirs \
  --delete
if $(which selinuxenabled 2>/dev/null); then
  restorecon -R src/ $PKGDIR/usr/share/yabsnap
fi

mkdir -p $PKGDIR/usr/bin
# Link needs to be to /usr/share/yabsnap/yabsnap.sh (without $PKGDIR/).
# That's where the file will reside after installation.
# Note: Do not use chmod on the symlink. A chmod on symlink is unnecessary,
# and also it will cause an error if the file does not exist.
ln -sf /usr/share/yabsnap/yabsnap.sh $PKGDIR/usr/bin/yabsnap

mkdir -p $PKGDIR/usr/lib/systemd/system
install -Z artifacts/services/yabsnap.service $PKGDIR/usr/lib/systemd/system
install -Z artifacts/services/yabsnap.timer $PKGDIR/usr/lib/systemd/system
if [[ -z "$PKGDIR" ]]; then
    # Reload if installed as root (i.e. $PKGDIR should be empty).
    # But not during AUR PKGBUILD, since it doesn't have system access.
    sudo systemctl daemon-reload
fi

readonly HOOKDIR=/usr/share/libalpm/hooks/
if [[ -d "$HOOKDIR" ]]; then
  mkdir -p $PKGDIR/$HOOKDIR
  install -Z artifacts/pacman/05-yabsnap-pacman-pre.hook $PKGDIR/$HOOKDIR
else
  printf 'Not an Arch based distro, will not install hook.\n' >&2
fi

mkdir -p $PKGDIR/usr/share/man/man1
# Note: makepkg will gzip automatically for Arch, but we gzip explicitly to
# support other distributions.
install -m 644 artifacts/yabsnap.manpage $PKGDIR/usr/share/man/man1/yabsnap.1
gzip -f $PKGDIR/usr/share/man/man1/yabsnap.1
