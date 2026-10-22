"""Read-only diagnostics: polling-rate check, raw button reports, movement counts (DPI check)."""
import os
import select
import struct
import time

from . import device


def _open_ro(path):
    try:
        return os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except PermissionError:
        raise device.DeviceError(device.HINT_PERMISSION % path)


def _pointer(profile):
    _, ptr = device.find_nodes(profile)
    if not ptr:
        raise device.DeviceError("no pointer interface found")
    return ptr


def _pointer_cfg(profile):
    # layout of the pointer report: report id, then little-endian signed 16-bit x and y at these offsets
    return profile.data["transport"].get("pointer_report", {"id": 1, "x": 2, "y": 4})


def measure(profile, seconds=4):
    """Reports per second while you move the mouse = polling rate."""
    node = _pointer(profile)
    fd = _open_ro(node)
    print("move the mouse continuously for %d s (%s)" % (seconds, node))
    n, end = 0, time.time() + seconds
    while time.time() < end:
        if select.select([fd], [], [], 0.1)[0]:
            try:
                os.read(fd, 64)
                n += 1
            except BlockingIOError:
                pass
    print("%d reports -> %d per second (while moving)" % (n, round(n / seconds)))


def watch(profile, seconds=20):
    """Print raw input reports of the command interface (button events such as the DPI button)."""
    fd = _open_ro(device.find_nodes(profile)[0])
    t0 = time.time()
    print("press mouse buttons now (%d s)" % seconds)
    while time.time() - t0 < seconds:
        if select.select([fd], [], [], 0.1)[0]:
            try:
                print("%6.2fs %s" % (time.time() - t0, os.read(fd, 64).hex(" ")), flush=True)
            except BlockingIOError:
                pass


def counts(profile, seconds=60):
    """Sum of |dx|+|dy| per swipe; swiping the same distance shows the DPI ratio between settings."""
    fd = _open_ro(_pointer(profile))
    cfg = _pointer_cfg(profile)
    print("swipe the same distance, change DPI, swipe again ... (%d s)" % seconds)
    total, last, k, t0 = 0, None, 0, time.time()
    while time.time() - t0 < seconds:
        if select.select([fd], [], [], 0.1)[0]:
            try:
                r = os.read(fd, 64)
            except BlockingIOError:
                continue
            if r and r[0] == cfg["id"]:
                dx = struct.unpack_from("<h", r, cfg["x"])[0]
                dy = struct.unpack_from("<h", r, cfg["y"])[0]
                total += abs(dx) + abs(dy)
                last = time.time()
        if last and time.time() - last > 0.5 and total:
            k += 1
            print("swipe %d: %d counts" % (k, total), flush=True)
            total, last = 0, None
