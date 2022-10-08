#!/bin/bash

set -uexo pipefail

# For AUR installation, everything must be done on a PKGDIR.
# The PKGDIR will be assumed to have the same structure as root.
readonly PKGDIR=${1-}

# Most of the installation will work on other distros;
# but certain things may not work - e.g. installation hooks.
if ! grep -q 'Arch Linux' /etc/issue; then
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
ln -sf $PKGDIR/usr/share/yabsnap/yabsnap.sh $PKGDIR/usr/bin/yabsnap

mkdir -p $PKGDIR/etc/systemd/system
cp artifacts/services/yabsnap.service $PKGDIR/etc/systemd/system
cp artifacts/services/yabsnap.timer $PKGDIR/etc/systemd/system

mkdir -p $PKGDIR/usr/share/libalpm/hooks/
cp artifacts/pacman/05-yabsnap-pacman-pre.hook $PKGDIR/usr/share/libalpm/hooks/
