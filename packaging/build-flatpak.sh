#!/usr/bin/env bash
# Build dist/pointerctl-<version>.flatpak. Needs flatpak, flatpak-builder and the GNOME SDK:
#   flatpak install flathub org.gnome.Sdk//50 org.gnome.Platform//50
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
ver="$(python3 -c 'import pointerctl; print(pointerctl.__version__)')"
id=io.github.naoomeow.Pointerctl
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
flatpak-builder --user --force-clean --disable-rofiles-fuse --state-dir="$work/state" --repo="$work/repo" "$work/build" "packaging/flatpak/$id.yml"
mkdir -p dist
flatpak build-bundle "$work/repo" "dist/pointerctl-$ver.flatpak" "$id"
echo "built dist/pointerctl-$ver.flatpak  (install with: flatpak install --user dist/pointerctl-$ver.flatpak)"
