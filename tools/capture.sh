#!/usr/bin/env bash
# Capture USB traffic of the mouse (30fa:1441) with usbmon.
# Usage: sudo ./capture.sh <name>     e.g.  sudo ./capture.sh dpi_change
# Press Ctrl+C to stop. Output: ../captures/<name>.pcapng
set -euo pipefail
name="${1:?give a capture name, e.g. dpi_change}"
here="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$here/../captures"
line="$(lsusb -d 30fa:1441 | head -1)"
[ -n "$line" ] || { echo "mouse 30fa:1441 not found"; exit 1; }
bus=$(echo "$line" | sed -E 's/Bus 0*([0-9]+) .*/\1/')
dev=$(echo "$line" | sed -E 's/.*Device 0*([0-9]+):.*/\1/')
modprobe usbmon
echo "bus=$bus device=$dev -> usbmon$bus ; Ctrl+C to stop"
out="$here/../captures/$name.pcapng"
[ ! -e "$out" ] || { echo "$out already exists; pick a new name"; exit 1; }
# dumpcap drops privileges and can't open $out itself, so let the root shell open it
dumpcap -q -i "usbmon$bus" -w - > "$out" &
pid=$!; trap 'kill $pid 2>/dev/null; wait $pid 2>/dev/null; chown "${SUDO_USER:-root}" "$out"; echo saved $out; echo "device address was $dev"' INT TERM
wait $pid
