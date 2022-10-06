set -uexo pipefail

# Most of the installation will work on other distros;
# but certain things may not work - e.g. installation hooks.
if ! grep -q 'Arch Linux' /etc/issue; then
  echo Not Arch based distro, not proceeding. >&2
  exit 1
fi

readonly MY_PATH=$(cd $(dirname "$0") && pwd)

cd $MY_PATH

rsync -aAXHSv src/ /usr/share/yabsnap \
  --exclude '*_test.py' \
  --include '*/' --include '*.py' --include '*.sh' \
  --exclude '*' \
  --prune-empty-dirs \
  --delete --delete-excluded
ln -sf /usr/share/yabsnap/yabsnap.sh /usr/bin/yabsnap

cp artifacts/services/yabsnap.service /etc/systemd/system
cp artifacts/services/yabsnap.timer /etc/systemd/system
systemctl daemon-reload
systemctl enable yabsnap.timer --now

cp artifacts/pacman/05-yabsnap-pacman-pre.hook /usr/share/libalpm/hooks/
