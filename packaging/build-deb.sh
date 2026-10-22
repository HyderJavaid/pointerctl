#!/usr/bin/env bash
# Build dist/pointerctl_<version>_all.deb (pure Python, no compilation). Needs dpkg-deb and fakeroot.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
ver="$(python3 -c 'import pointerctl; print(pointerctl.__version__)')"
pkg=pointerctl
id=io.github.naoomeow.Pointerctl
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
chmod 755 "$stage"

py="$stage/usr/lib/python3/dist-packages"
install -d "$py" "$stage/usr/bin" "$stage/usr/share/applications" "$stage/usr/share/metainfo" \
  "$stage/usr/share/icons/hicolor/scalable/apps" "$stage/usr/lib/udev/rules.d" \
  "$stage/usr/share/doc/$pkg" "$stage/DEBIAN"

cp -r pointerctl "$py/"
find "$py" -name __pycache__ -prune -exec rm -rf {} +
find "$py" -type d -exec chmod 755 {} + ; find "$py" -type f -exec chmod 644 {} +

printf '#!/usr/bin/python3\nfrom pointerctl.cli import main\n\nmain()\n' > "$stage/usr/bin/pointerctl"
printf '#!/usr/bin/python3\nfrom pointerctl.gui.app import main\n\nraise SystemExit(main())\n' > "$stage/usr/bin/pointerctl-gui"
chmod 755 "$stage/usr/bin/pointerctl" "$stage/usr/bin/pointerctl-gui"

install -m 644 "packaging/data/$id.desktop" "$stage/usr/share/applications/"
install -m 644 "packaging/data/$id.metainfo.xml" "$stage/usr/share/metainfo/"
install -m 644 "packaging/data/$id.svg" "$stage/usr/share/icons/hicolor/scalable/apps/"
install -m 644 udev/70-pointerctl.rules "$stage/usr/lib/udev/rules.d/70-pointerctl.rules"
install -m 644 LICENSE "$stage/usr/share/doc/$pkg/copyright"
gzip -9n -c README.md > "$stage/usr/share/doc/$pkg/README.md.gz"
printf '%s (%s) unstable; urgency=low\n\n  * Release %s.\n\n -- pointerctl contributors <111737483+naOomeow@users.noreply.github.com>  Thu, 22 Oct 2026 00:00:00 +0000\n' "$pkg" "$ver" "$ver" | gzip -9n > "$stage/usr/share/doc/$pkg/changelog.gz"
chmod 644 "$stage"/usr/share/doc/$pkg/*

size="$(du -sk --exclude=DEBIAN "$stage" | cut -f1)"
cat > "$stage/DEBIAN/control" <<EOF
Package: $pkg
Version: $ver
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.9), python3-gi, gir1.2-gtk-4.0, gir1.2-adw-1
Installed-Size: $size
Maintainer: pointerctl contributors <111737483+naOomeow@users.noreply.github.com>
Homepage: https://github.com/naOomeow/pointerctl
Description: unofficial settings tool for mice
 Change DPI levels, polling rate, button functions (including keyboard
 shortcuts and media keys) and lighting on a supported mouse without the
 manufacturer's Windows software. Currently supports the GM21.
 .
 Installs a udev rule so the logged-in user can access the mouse; unplug and
 replug the mouse once after installing. Not affiliated with any manufacturer.
EOF
cat > "$stage/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = configure ] && command -v udevadm >/dev/null 2>&1; then
    udevadm control --reload || true
    udevadm trigger --action=change --subsystem-match=hidraw || true
fi
exit 0
EOF
cat > "$stage/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e
if command -v udevadm >/dev/null 2>&1; then udevadm control --reload || true; fi
exit 0
EOF
chmod 755 "$stage/DEBIAN/postinst" "$stage/DEBIAN/postrm" "$stage/DEBIAN"

mkdir -p dist
fakeroot dpkg-deb --build --root-owner-group "$stage" "dist/${pkg}_${ver}_all.deb" >/dev/null
echo "built dist/${pkg}_${ver}_all.deb"
