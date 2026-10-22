"""Frame-template engine.

A profile "action" is a list of 8-byte feature-report frames (the template, captured from the
manufacturer's software) plus patches.  A patch says: for every frame matching a pattern, set (part of) one
byte to the value of an expression over the named parameters.  This is all a contributor
needs to describe a mouse without writing Python.

Expressions are parsed with `ast` and only a small whitelist of operations is evaluated, so a
profile from the internet cannot run arbitrary code.
"""
import ast
import json
import operator
import os

_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.BitAnd: operator.and_,
        ast.BitOr: operator.or_, ast.BitXor: operator.xor, ast.LShift: operator.lshift,
        ast.RShift: operator.rshift}
_CMP = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt, ast.LtE: operator.le,
        ast.Gt: operator.gt, ast.GtE: operator.ge}


class ProfileError(Exception):
    pass


def evaluate(expr, env, funcs=None):
    funcs = funcs or {}

    def ev(n):
        if isinstance(n, ast.Constant):
            return n.value
        if isinstance(n, ast.Name):
            if n.id not in env:
                raise ProfileError("unknown name %r in expression %r" % (n.id, expr))
            return env[n.id]
        if isinstance(n, ast.BinOp) and type(n.op) in _BIN:
            return _BIN[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp):
            v = ev(n.operand)
            if isinstance(n.op, ast.USub):
                return -v
            if isinstance(n.op, ast.Invert):
                return ~v
            if isinstance(n.op, ast.Not):
                return not v
        if isinstance(n, ast.BoolOp):
            vals = [ev(v) for v in n.values]
            return all(vals) if isinstance(n.op, ast.And) else any(vals)
        if isinstance(n, ast.Compare) and all(type(o) in _CMP for o in n.ops):
            left = ev(n.left)
            for op, right in zip(n.ops, n.comparators):
                r = ev(right)
                if not _CMP[type(op)](left, r):
                    return False
                left = r
            return True
        if isinstance(n, ast.IfExp):
            return ev(n.body) if ev(n.test) else ev(n.orelse)
        if isinstance(n, ast.Subscript):
            sl = n.slice.value if isinstance(n.slice, getattr(ast, "Index", ())) else n.slice   # python 3.8 wraps the index
            return ev(n.value)[ev(sl)]
        if isinstance(n, (ast.Tuple, ast.List)):
            return [ev(e) for e in n.elts]
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in funcs and not n.keywords:
            return funcs[n.func.id](*[ev(a) for a in n.args])
        raise ProfileError("expression %r uses something not allowed (%s)" % (expr, type(n).__name__))

    try:
        return ev(ast.parse(expr, mode="eval").body)
    except SyntaxError as e:
        raise ProfileError("bad expression %r: %s" % (expr, e))


def parse_pattern(pat):
    """'0718030d0800??17' -> [(index, byte-or-None), ...]; '??' matches any byte."""
    pat = pat.replace(" ", "").lower()
    if len(pat) != 16:
        raise ProfileError("pattern %r must be 8 bytes (16 hex digits, ?? = any)" % pat)
    return [(i, None if pat[2 * i:2 * i + 2] == "??" else int(pat[2 * i:2 * i + 2], 16)) for i in range(8)]


def _coerce(name, spec, value, tables):
    """Check/convert a command-line or API value against a field spec."""
    kind = spec.get("type", "int")
    if isinstance(value, str) and any(value.startswith(p) for p in spec.get("allow_prefix", [])):
        return value                                  # free-form value checked by a builder (e.g. "shortcut:ctrl+c")
    if kind == "int":
        value = int(value)
        lo, hi = spec.get("min"), spec.get("max")
        if (lo is not None and value < lo) or (hi is not None and value > hi):
            raise ProfileError("%s must be between %s and %s" % (name, lo, hi))
        return value
    choices = spec.get("choices")
    if choices is None:
        choices = tables[spec["choices_from"]]
    if choices and isinstance(choices[0], int):
        value = int(value)
    if value not in choices:
        raise ProfileError("%s must be one of: %s" % (name, ", ".join(str(c) for c in choices)))
    return value


class Profile:
    def __init__(self, path):
        self.dir = path
        with open(os.path.join(path, "profile.json")) as f:
            self.data = json.load(f)
        self.id = self.data["id"]
        self.name = self.data["name"]
        self.tables = self.data.get("tables", {})
        self.actions = self.data.get("actions", {})
        self._templates = {}

    def template(self, rel):
        if rel not in self._templates:
            with open(os.path.join(self.dir, rel)) as f:
                self._templates[rel] = f.read().split()
        return self._templates[rel]

    def params(self, action):
        """Field specs of an action, with defaults."""
        return self.actions[action]["fields"]

    def resolve(self, action, given):
        fields = self.params(action)
        unknown = set(given) - set(fields)
        if unknown:
            raise ProfileError("unknown parameter(s) for '%s': %s" % (action, ", ".join(sorted(unknown))))
        return {n: _coerce(n, s, given[n], self.tables) if n in given else s["default"] for n, s in fields.items()}

    def build(self, action, given=None):
        """Return the frames (list of 16-hex-digit strings) for an action with the given parameters."""
        act = self.actions[action]
        values = self.resolve(action, given or {})
        funcs = {"idx": lambda t, v: self.tables[t].index(v),
                 "tbl": lambda t, k: self.tables[t][str(k)],
                 "min": min, "max": max, "sum": sum}
        from . import builders
        hooks = [(builders.REGISTRY[b["name"]], b) for b in act.get("builders", [])]
        states = []
        for hook, spec in hooks:
            values, state = hook.prepare(values, spec)
            states.append(state)
        env = dict(values)
        for name, expr in act.get("derived", {}).items():
            env[name] = evaluate(expr, env, funcs)
        for chk in act.get("checks", []):
            if not evaluate(chk["expr"], env, funcs):
                raise ProfileError(chk["error"])
        frames = [bytearray.fromhex(f) for f in self.template(act["template"].format(**values))]
        for p in act["patches"]:
            if "when" in p and not evaluate(p["when"], env, funcs):
                continue
            pat = parse_pattern(p["match"])
            byte, mask = p.get("byte", 6), p.get("mask", 0xff)
            new = evaluate(p["expr"], env, funcs) & mask if mask != 0xff else evaluate(p["expr"], env, funcs)
            if not 0 <= new <= 255:
                raise ProfileError("value %d out of byte range for pattern %s" % (new, p["match"]))
            for fr in frames:
                if all(want is None or fr[i] == want for i, want in pat):
                    fr[byte] = (fr[byte] & ~mask & 0xff) | new
        for (hook, spec), state in zip(hooks, states):
            frames = hook.finish(frames, state, spec)
        return [fr.hex() for fr in frames]
