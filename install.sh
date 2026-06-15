#!/bin/bash
# Full installation of fingerprint reader support for HP EliteBook G5 (138a:00ab)
# Run as root or with sudo.
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEM_DIR="/usr/local/lib/validity-patch"

echo "=== 1. PPA and packages ==="
add-apt-repository -y ppa:uunicorn/open-fprintd
apt update
apt install -y python3-validity open-fprintd cabextract

echo ""
echo "=== 2. Copy patch.py to system directory ==="
mkdir -p "$SYSTEM_DIR"
cp "$REPO_DIR/patch.py" "$SYSTEM_DIR/patch.py"

echo ""
echo "=== 3. Patch python3-validity ==="
python3 "$SYSTEM_DIR/patch.py"

echo ""
echo "=== 4. Build and install fprintd-tools ==="
bash "$REPO_DIR/fprintd-tools/build.sh"
dpkg -i /tmp/fprintd-tools_*_amd64.deb

echo ""
echo "=== 5. PAM ==="
pam-auth-update --enable fprintd

echo ""
echo "=== 6. Udev and services ==="
udevadm control --reload-rules
udevadm trigger
systemctl enable --now python3-validity open-fprintd

echo ""
echo "=== 7. Apt hook (re-apply patches after upgrades) ==="
cp "$REPO_DIR/apt-hook/99validity-patch" /etc/apt/apt.conf.d/99validity-patch

echo ""
echo "=== 8. Resume hook (restart driver after standby) ==="
cp "$REPO_DIR/sleep-hook/python3-validity" /lib/systemd/system-sleep/python3-validity
chmod +x /lib/systemd/system-sleep/python3-validity

echo ""
echo "=== 9. Firmware ==="
validity-sensors-firmware

echo ""
echo "=== 10. Installation complete ==="
echo "Enroll your fingerprints with: fprintd-enroll"
echo "Verify with:                   fprintd-verify"
