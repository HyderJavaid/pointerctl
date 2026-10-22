"""Command line: pointerctl list | identify | params | diag | <action> key=value ... [--yes]"""
import argparse
import sys

from . import __version__, device, diag, profiles
from .engine import ProfileError

EPILOG = """examples:
  pointerctl list                                   which connected devices are supported
  pointerctl params config                          parameters of the 'config' action
  pointerctl config dpi1=800 dpi2=1600 rate=1000    dry run: builds the frames, sends nothing
  pointerctl config dpi1=800 rate=1000 --yes        send them to the mouse
  pointerctl solid color=red brightness=5 --yes
  pointerctl diag measure                           check the polling rate (move the mouse)
Unknown commands are treated as profile actions (see `pointerctl params`)."""


def _pick_profile(name):
    if name:
        return profiles.load(name)
    devs = device.hidraw_devices()
    for p in profiles.all_profiles().values():
        if any(device.matches(p, d) for d in devs):
            return p
    found = profiles.all_profiles()
    if len(found) == 1:                       # nothing connected: still let `params` and dry runs work
        return next(iter(found.values()))
    raise ProfileError("no supported device connected; use --profile (profiles: %s)" % ", ".join(found))


def cmd_list(_):
    devs = device.hidraw_devices()
    allp = profiles.all_profiles()
    for d in devs:
        sup = [p.name for p in allp.values() if device.matches(p, d)]
        print("%-12s %04x:%04x  %-32s %s" % (d["node"], d["vid"], d["pid"], d["name"], ("supported: " + sup[0]) if sup else "-"))
    print("profiles: " + (", ".join("%s (%s)" % (p.id, p.data.get("status", "?")) for p in allp.values()) or "none"))


def cmd_identify(_):
    """Read-only: everything needed for a bug report or a new profile."""
    for d in device.hidraw_devices():
        print("%s  %04x:%04x  %s" % (d["node"], d["vid"], d["pid"], d["name"]))
        print("  report descriptor (%d bytes): %s" % (len(d["descriptor"]), d["descriptor"].hex(" ")))


def cmd_params(profile, rest):
    acts = profile.actions
    for name in ([rest[0]] if rest else list(acts)):
        if name not in acts:
            raise ProfileError("no action %r (have: %s)" % (name, ", ".join(acts)))
        print("%s - %s" % (name, acts[name].get("description", "")))
        for f, s in acts[name]["fields"].items():
            choices = s.get("choices") or profile.tables.get(s.get("choices_from", ""), [])
            rng = ("%s..%s" % (s.get("min"), s.get("max"))) if s.get("type", "int") == "int" else (
                ", ".join(map(str, choices)) if len(choices) <= 8 else "%s .. %s (%d values)" % (choices[0], choices[-1], len(choices)))
            print("  %-15s default %-14s %-28s %s" % (f, s["default"], rng, s.get("help", "")))


def cmd_diag(profile, rest):
    fns = {"measure": diag.measure, "watch": diag.watch, "counts": diag.counts}
    if not rest or rest[0] not in fns:
        raise ProfileError("diag needs one of: " + ", ".join(fns))
    fns[rest[0]](profile)


def cmd_action(profile, action, rest):
    send = "--yes" in rest
    given = {}
    for tok in rest:
        if tok == "--yes":
            continue
        if "=" not in tok:
            raise ProfileError("expected key=value, got %r" % tok)
        k, v = tok.split("=", 1)
        given[k] = v
    frames = profile.build(action, given)
    if not send:
        print("%d frames built for %s '%s' (dry run; add --yes to send)" % (len(frames), profile.name, action))
        return
    node = device.find_nodes(profile)[0]
    print("sending %d frames to %s ..." % (len(frames), node))
    device.send(profile, frames, node)
    print("done")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pointerctl", description="Unofficial mouse configuration for Linux (not affiliated with any manufacturer).",
                                 epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version="pointerctl " + __version__)
    ap.add_argument("--profile", help="profile id (default: detected from the connected device)")
    ap.add_argument("command", help="list | identify | params | diag | <profile action>")
    ap.add_argument("rest", nargs=argparse.REMAINDER)
    a = ap.parse_args(argv)
    try:
        if a.command == "list":
            return cmd_list(a.rest)
        if a.command == "identify":
            return cmd_identify(a.rest)
        profile = _pick_profile(a.profile)
        if a.command == "params":
            return cmd_params(profile, a.rest)
        if a.command == "diag":
            return cmd_diag(profile, a.rest)
        if a.command not in profile.actions:
            raise ProfileError("unknown command or action %r (actions of %s: %s)" % (a.command, profile.id, ", ".join(profile.actions)))
        return cmd_action(profile, a.command, a.rest)
    except (ProfileError, device.DeviceError) as e:
        sys.exit("pointerctl: %s" % e)


if __name__ == "__main__":
    main()
