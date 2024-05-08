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

readonly PKGNAME=yabsnap

# This mirrors PKGBUILD with slight modifications.
pushd src/
tar -cf - \
  $(find -type f -not -name "*_test.py" \( -name "*.py" -o -name "*.conf" \)) |
  tar -xf - -C "$PKGDIR"/usr/share/"$PKGNAME"/
pushd "$PKGDIR"/usr/share/"$PKGNAME"/
chown -R root:root .
chmod -R u=rwX,go=rX .
popd
popd

cd artifacts
install -Dm 644 services/"$PKGNAME".{service,timer}      -t "$PKGDIR"/usr/lib/systemd/system/
install -Dm 664 pacman/*.hook     -t "$PKGDIR"/usr/share/libalpm/hooks/
install -Dm 644 yabsnap.manpage   "$PKGDIR"/usr/share/man/man1/yabsnap.1
gzip -f "$PKGDIR"/usr/share/man/man1/"$PKGNAME".1
cd ../src
install -Dm 755 "$PKGNAME".sh -t "$PKGDIR"/usr/share/"$PKGNAME"/
install -d "$PKGDIR"/usr/bin
ln -sf /usr/share/"$PKGNAME"/"$PKGNAME".sh "$PKGDIR"/usr/bin/"$PKGNAME"
