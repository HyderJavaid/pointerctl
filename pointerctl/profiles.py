"""Find device profiles: built-in ones (pointerctl/profiles/<id>/) plus the user's own in ~/.config/pointerctl/profiles/."""
import os

from .engine import Profile, ProfileError

BUILTIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles")
USER = os.path.expanduser(os.environ.get("POINTERCTL_PROFILES", "~/.config/pointerctl/profiles"))


def all_profiles():
    found = {}
    for root in (BUILTIN, USER):          # a user profile with the same id overrides the built-in one
        if os.path.isdir(root):
            for name in sorted(os.listdir(root)):
                if os.path.exists(os.path.join(root, name, "profile.json")):
                    p = Profile(os.path.join(root, name))
                    found[p.id] = p
    return found


def load(pid):
    try:
        return all_profiles()[pid]
    except KeyError:
        raise ProfileError("no profile named %r (have: %s)" % (pid, ", ".join(all_profiles()) or "none"))
