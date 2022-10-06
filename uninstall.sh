set -uexo pipefail

readonly MY_PATH=$(cd $(dirname "$0") && pwd)

cd $MY_PATH

rm -f /usr/share/libalpm/hooks/05-yabsnap-pacman-pre.hook

systemctl disable yabsnap.timer || true
systemctl daemon-reload
rm -f /etc/systemd/system/yabsnap.service
rm -f /etc/systemd/system/yabsnap.timer

rm -f /usr/bin/yabsnap
rm -rf /usr/share/yabsnap 2> /dev/null
