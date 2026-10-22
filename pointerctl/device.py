"""hidraw discovery and feature-report I/O (Linux ioctls, no dependencies)."""
import fcntl
import glob
import os
import time

HINT_PERMISSION = ("permission denied on %s - install the udev rule (see README: ./udev/install.sh), "
                   "then unplug and replug the mouse")


class DeviceError(Exception):
    pass


def _ioc(nr, length):                       # _IOC(RW, 'H', nr, len)
    return (3 << 30) | (length << 16) | (ord("H") << 8) | nr


def hidraw_devices():
    """All hidraw nodes with vendor/product id, name and report descriptor (read-only, no device access)."""
    out = []
    for d in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        try:
            with open(d + "/device/uevent") as f:
                ue = dict(line.split("=", 1) for line in f.read().splitlines() if "=" in line)
            _, vid, pid = ue["HID_ID"].split(":")
            with open(d + "/device/report_descriptor", "rb") as f:
                desc = f.read()
        except (OSError, KeyError, ValueError):
            continue
        out.append({"node": "/dev/" + os.path.basename(d), "vid": int(vid, 16), "pid": int(pid, 16),
                    "name": ue.get("HID_NAME", ""), "descriptor": desc})
    return out


def matches(profile, dev):
    m = profile.data["match"]
    if dev["vid"] != int(m["vid"], 16) or dev["pid"] != int(m["pid"], 16):
        return False
    # Models share USB ids; only the one the profile was written for is accepted unless POINTERCTL_FORCE=1.
    return os.environ.get("POINTERCTL_FORCE") == "1" or m.get("name_contains", "") in dev["name"]


def _has_command_interface(profile, dev):
    needle = bytes.fromhex(profile.data["transport"]["command_descriptor_contains"].replace(" ", ""))
    return needle in dev["descriptor"]


def find_nodes(profile):
    """(command node, pointer node or None) of the first connected device that matches the profile."""
    cmd = ptr = None
    for dev in hidraw_devices():
        if matches(profile, dev):
            if _has_command_interface(profile, dev):
                cmd = cmd or dev["node"]
            else:
                ptr = ptr or dev["node"]
    if not cmd:
        raise DeviceError("no %s found (set POINTERCTL_FORCE=1 to try a different model with the same USB id - at your own risk)" % profile.name)
    return cmd, ptr


def _delay(transport, frame):
    for rule in transport.get("delay_rules", []):
        if rule.get("frame") == frame or ("prefix" in rule and frame.startswith(rule["prefix"])):
            return rule["ms"] / 1000
    return transport.get("default_delay_ms", 3) / 1000


def send(profile, frames, node=None):
    """Send frames as HID feature reports, with the pacing observed on the wire."""
    node = node or find_nodes(profile)[0]
    tr = profile.data["transport"]
    rid, size = tr["report_id"], 8
    try:
        fd = os.open(node, os.O_RDWR)
    except PermissionError:
        raise DeviceError(HINT_PERMISSION % node)
    try:
        for f in frames:
            fcntl.ioctl(fd, _ioc(0x06, size), bytearray.fromhex(f))                 # HIDIOCSFEATURE
            if any(f.startswith(p) for p in tr.get("get_after_prefix", [])):         # a read-back follows these frames on the wire
                time.sleep(0.002)
                fcntl.ioctl(fd, _ioc(0x07, size), bytearray([rid] + [0] * (size - 1)))   # HIDIOCGFEATURE
            time.sleep(_delay(tr, f))
    finally:
        os.close(fd)
