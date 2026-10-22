#!/usr/bin/env bash
# Install the udev rule so your normal user can talk to supported mice (no root needed to run pointerctl).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
sudo install -m 644 "$here/70-pointerctl.rules" /etc/udev/rules.d/70-pointerctl.rules
sudo udevadm control --reload
sudo udevadm trigger --action=change --subsystem-match=hidraw
echo "Installed /etc/udev/rules.d/70-pointerctl.rules. If 'pointerctl' still says permission denied, unplug and replug the mouse."
