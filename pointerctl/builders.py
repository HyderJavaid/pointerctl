"""Builders: the few things the patch language cannot express (variable-length data).

A builder is named in an action's "builders" list in profile.json and configured there.  It has two steps:
  prepare(values, spec) -> (values, state)   called before patching; may replace field values
  finish(frames, state, spec) -> frames      called after patching; may edit or insert frames
"""
from .engine import ProfileError

MODIFIERS = {"ctrl": 0xe0, "shift": 0xe1, "alt": 0xe2, "win": 0xe3}      # HID keyboard usage ids (public standard)
KEYS = {c: 4 + i for i, c in enumerate("abcdefghijklmnopqrstuvwxyz")}
KEYS.update({c: 30 + i for i, c in enumerate("1234567890")})
KEYS.update({"enter": 40, "esc": 41, "backspace": 42, "tab": 43, "space": 44, "insert": 73, "home": 74, "pageup": 75,
             "delete": 76, "end": 77, "pagedown": 78, "right": 79, "left": 80, "down": 81, "up": 82})
KEYS.update({"f%d" % i: 57 + i for i in range(1, 13)})


def macro_bytes(text, spec):
    """'ctrl+c' -> the 12-byte event list the mouse stores for a <modifier>+<key> shortcut."""
    parts = text.lower().split("+")
    if len(parts) != 2 or parts[0] not in MODIFIERS or parts[1] not in KEYS:
        raise ProfileError("shortcut must look like <modifier>+<key>, modifier one of %s, key a-z, 0-9, f1-f12, enter, esc, tab, space, "
                           "backspace, delete, insert, home, end, pageup, pagedown or an arrow (got %r)" % (", ".join(MODIFIERS), text))
    mod, key = MODIFIERS[parts[0]], KEYS[parts[1]]
    d1, d2, d3, d4 = spec["delays"].get("+".join(parts), spec["delays"]["default"])
    # 01 00 | (d1+1) mod | 7f 00 | (d2|0x80) key | d3 key | d4 mod   (layout seen in captures; delays are values observed on the wire)
    return [1, 0, (d1 + 1) & 255, mod, 0x7f, 0, d2 | 0x80, key, d3, key, d4, mod]


def _set(frames, page, idx, value, bank=0):
    for fr in frames:
        if fr[1] == 0x18 and fr[2] == 3 and fr[3] == idx and fr[4] == page and fr[5] == bank:
            fr[6] = value
            return
    raise ProfileError("template has no frame for page 0x%02x idx %d" % (page, idx))


def _set_n(frames, n, value, spec):
    """Byte n of the side table (pages laid end to end, 32 bytes each)."""
    _set(frames, spec["side_table_page"] + 32 * (n // 32), n % 32, value)


class InstantMacros:
    """Keyboard shortcuts on buttons: event lists in a macro bank, start offsets in per-button side-table entries,
    slot pointers in a page.  Layout derived from captures kb7-kb10 (see docs/protocol-gm21.md)."""

    @staticmethod
    def prepare(values, spec):
        values, macros = dict(values), {}
        for field in spec["fields"]:
            v = values[field]
            if isinstance(v, str) and v.startswith("shortcut:"):
                macros[field] = macro_bytes(v[len("shortcut:"):], spec)
                values[field] = "shortcut"
        return values, macros

    @staticmethod
    def finish(frames, macros, spec):
        if not macros:
            return frames
        order = spec["order"]                                    # button field -> index k; macros are stored in k order
        used = sorted(order, key=order.get)
        cum, offset = 0, {}
        for f in used:
            offset[f] = cum
            cum += len(macros.get(f, []))
        if cum + 4 * 8 > 255:
            raise ProfileError("macro memory full")
        stride = spec["entry_stride"]
        for f in used:
            e = stride * order[f]
            if offset[f]:
                _set_n(frames, e + 5, offset[f], spec)           # offset of this button's macro / of the next macro
            if f in macros:
                m = macros[f]
                _set_n(frames, e + 1, (len(m) - 2) // 2, spec)    # number of key events
                _set_n(frames, e + 6, 4, spec)                    # entry type
                _set_n(frames, e + 8, len(m) - 2, spec)           # bytes of event data
        for j, idx in enumerate(spec["pointer_idx"]):            # four 8-byte user-macro slots follow the shortcut macros
            _set(frames, spec["pointer_page"], idx, cum + 8 * j)
        data = [b for f in used for b in macros.get(f, [])]
        extra = []
        for base in range(0, len(data), 32):
            chunk, n = data[base:base + 32], min(32, len(data) - base)
            for i, b in enumerate(chunk):
                extra.append(bytearray([7, 0x18, 3, i, base, spec["bank"], b, n - 1]))
            extra.append(bytearray([7, 0x18, 9, 0, base, spec["bank"], 0, n - 1]))
            extra.append(bytearray([7, 0x18, 0, 0, base, spec["bank"], 0, 0]))
        anchor = bytearray.fromhex(spec["anchor"])
        pos = next((i for i, fr in enumerate(frames) if fr == anchor), None)
        if pos is None:
            raise ProfileError("anchor frame %s not found in template" % spec["anchor"])
        return frames[:pos] + extra + frames[pos:]


REGISTRY = {"instant_macros": InstantMacros}
