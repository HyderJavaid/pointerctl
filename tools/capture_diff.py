#!/usr/bin/env python3
"""Turn usbmon captures into frame lists and show what changed between two captures.

  tools/capture_diff.py --extract cap.pcapng > cap.seq        frames sent to the mouse, one 8-byte report per line
  tools/capture_diff.py before.pcapng after.pcapng            which frames changed (also accepts .seq files)

Workflow for a new mouse: capture the manufacturer's configuration software doing ONE change at a time (see docs/adding-a-mouse.md), diff
each capture against a baseline, and write down which byte changed for which setting.
Needs tshark.  Frames are the data of control transfers to endpoint 0 (HID SET_REPORT feature reports).
"""
import argparse
import collections
import subprocess
import sys


def extract(path, device=None):
    out = subprocess.run(["tshark", "-r", path, "-Y", "usb.endpoint_address.number==0 && usb.data_fragment", "-T", "fields",
                          "-e", "usb.device_address", "-e", "usb.endpoint_address", "-e", "usb.data_fragment"],
                         capture_output=True, text=True, check=True).stdout.splitlines()
    rows = [l.split("\t") for l in out if l.count("\t") == 2]
    rows = [r for r in rows if int(r[1], 16) == 0]                       # host -> device only
    if not rows:
        return []
    if device is None:                                                    # the device that received the most data
        device = collections.Counter(r[0] for r in rows).most_common(1)[0][0]
    return [r[2] for r in rows if r[0] == device]


def load(path, device):
    if path.endswith(".seq"):
        with open(path) as f:
            return f.read().split()
    return extract(path, device)


def describe(frame):
    """Best-effort reading of the GM21-style 'write one byte' frame: 07 18 03 <idx> <base> <bank> <value> <len-1>."""
    b = bytes.fromhex(frame)
    if len(b) == 8 and b[1] == 0x18 and b[2] == 3:
        return "  (base 0x%02x bank %d idx %d = 0x%02x)" % (b[4], b[5], b[3], b[6])
    return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--extract", action="store_true", help="print the frames of one capture")
    ap.add_argument("--device", help="USB device address (default: the one that received most data)")
    a = ap.parse_args()
    if a.extract:
        print("\n".join(load(a.files[0], a.device)))
        return
    if len(a.files) != 2:
        ap.error("give two files to diff")
    x, y = load(a.files[0], a.device), load(a.files[1], a.device)
    print("%d frames vs %d frames" % (len(x), len(y)))
    if len(x) == len(y):
        changed = [(i, p, q) for i, (p, q) in enumerate(zip(x, y)) if p != q]
        for i, p, q in changed:
            print("frame %4d: %s -> %s%s" % (i, p, q, describe(q)))
        print("%d frame(s) differ" % len(changed))
    else:                                       # different lengths: compare as multisets
        cx, cy = collections.Counter(x), collections.Counter(y)
        for f in sorted(cx - cy):
            print("only in first : %s  x%d%s" % (f, (cx - cy)[f], describe(f)))
        for f in sorted(cy - cx):
            print("only in second: %s  x%d%s" % (f, (cy - cx)[f], describe(f)))


if __name__ == "__main__":
    sys.exit(main())
