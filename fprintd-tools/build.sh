#!/bin/bash
# Builds the local fprintd-tools package by extracting client binaries
# and pam_fprintd.so from the official fprintd package, without installing
# the daemon (which conflicts with open-fprintd).
set -e

PKG_DIR=$(mktemp -d)
trap "rm -rf $PKG_DIR" EXIT

VERSION="1.94.3-local2"
OUT_DEB="/tmp/fprintd-tools_${VERSION}_amd64.deb"

echo "=== Extracting binaries from fprintd and libpam-fprintd ==="
FPRINTD_DIR=$(mktemp -d)
LIBPAM_DIR=$(mktemp -d)
trap "rm -rf $PKG_DIR $FPRINTD_DIR $LIBPAM_DIR" EXIT

cd /tmp
apt-get download fprintd libpam-fprintd
dpkg-deb -x fprintd_*.deb "$FPRINTD_DIR"
dpkg-deb -x libpam-fprintd_*.deb "$LIBPAM_DIR"
rm -f fprintd_*.deb libpam-fprintd_*.deb

echo "=== Building package structure ==="
mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/usr/bin"
mkdir -p "$PKG_DIR/usr/lib/x86_64-linux-gnu/security"
mkdir -p "$PKG_DIR/usr/share/pam-configs"

cp "$FPRINTD_DIR/usr/bin/fprintd-"* "$PKG_DIR/usr/bin/"
chmod 755 "$PKG_DIR/usr/bin/fprintd-"*

cp "$LIBPAM_DIR/usr/lib/x86_64-linux-gnu/security/pam_fprintd.so" \
   "$PKG_DIR/usr/lib/x86_64-linux-gnu/security/"

# pam-configs with parameters tuned for the 0xd51 chip:
# - max-tries=3: 3 attempts before password fallback
# - timeout=8: after 8s without a read, the password field becomes active
cat > "$PKG_DIR/usr/share/pam-configs/fprintd" << 'PAMEOF'
Name: Fingerprint authentication
Default: no
Priority: 260
Conflicts: fprint
Auth-Type: Primary
Auth:
	[success=end default=ignore]	pam_fprintd.so max-tries=3 timeout=8
PAMEOF

cat > "$PKG_DIR/DEBIAN/control" << CTRLEOF
Package: fprintd-tools
Version: $VERSION
Architecture: amd64
Maintainer: local
Depends: libglib2.0-0, libdbus-1-3
Description: Fingerprint client tools (without fprintd daemon)
 Contains fprintd-enroll, fprintd-verify, fprintd-list, fprintd-delete
 and pam_fprintd.so. Designed to work with open-fprintd +
 python3-validity instead of the standard fprintd daemon.
 PAM parameters: max-tries=3 timeout=8 (tuned for 0xd51 chip).
CTRLEOF

cat > "$PKG_DIR/DEBIAN/postinst" << 'POSTEOF'
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    pam-auth-update --package --enable fprintd || true
fi
POSTEOF
chmod 755 "$PKG_DIR/DEBIAN/postinst"

dpkg-deb --build "$PKG_DIR" "$OUT_DEB"
echo "=== Package created: $OUT_DEB ==="
echo "To install: sudo dpkg -i $OUT_DEB"
