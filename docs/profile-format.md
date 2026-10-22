# Profile format

A profile is a folder `pointerctl/profiles/<id>/` (or `~/.config/pointerctl/profiles/<id>/`) containing `profile.json`
and the template frame files it references. The GM21 profile is a complete, tested example.

## profile.json

```jsonc
{
  "id": "gm21", "name": "Meetion GM21", "status": "tested on one unit",
  "match": { "vid": "30fa", "pid": "1441", "name_contains": "GM21" },
  "transport": {
    "report_id": 7,                                  // HID feature report id, 8 bytes including the id
    "command_descriptor_contains": "06 01 ff",       // bytes in the report descriptor that identify the config interface
    "get_after_prefix": ["071805"],                  // frames that are followed by a read-back on the wire
    "default_delay_ms": 3,
    "delay_rules": [ {"frame": "0718500000000000", "ms": 5}, {"prefix": "071809", "ms": 9} ],
    "pointer_report": { "id": 1, "x": 2, "y": 4 }    // optional: layout of the mouse movement report (for `diag counts`)
  },
  "tables": { "dpi_steps": [200, 400, ...], "rate_byte": {"1000": 0, "500": 1} },
  "actions": { "config": { ... } }
}
```

`match.name_contains` matters: models of one family often share vid/pid, so the profile is only used for devices whose
name contains that text (unless the user sets `POINTERCTL_FORCE=1`).

## An action

```jsonc
"config": {
  "description": "what the manufacturer's software sends on 'apply'",
  "template": "config.seq",              // frames to start from; may contain {param}, e.g. "effects/{mode}.seq"
  "fields": {                            // the parameters the user can set
    "rate": { "type": "choice", "choices": [125, 250, 500, 1000], "default": 500, "help": "polling rate in Hz" },
    "debounce_ms": { "type": "int", "min": 19, "max": 300, "default": 100 },
    "dpi1": { "type": "choice", "choices_from": "dpi_steps", "default": 1200 }
  },
  "derived": { "s1": "idx('dpi_steps', dpi1) + 1" },          // optional named values, evaluated in order
  "checks":  [ { "expr": "rate >= 125", "error": "message" } ],  // must all be true
  "patches": [
    { "match": "071803120800??17", "expr": "debounce_ms // 8" },
    { "match": "0718031a2000??1f", "expr": "(10 if rate == 500 else 9) | (symmetry << 6)" },
    { "match": "071803001c00????", "expr": "frequency - 1", "mask": 15, "when": "mode != 'off'" }
  ]
}
```

- **Frames** are 8 bytes written as 16 hex digits.
- **`match`** is a 16-digit pattern; `??` matches any byte. Every frame in the template that matches is patched.
- **`byte`** (default 6) is the index of the byte to change; **`mask`** (default `0xff`) limits the change to some
  bits, so two settings can share a byte (for example a low nibble and a high nibble).
- **`when`** skips the patch when false.
- Field values are ints, or strings for choice fields whose choices are strings.

## Expressions

Integer arithmetic and logic: `+ - * // % & | ^ << >> ~`, comparisons, `and`/`or`/`not`, `x if cond else y`,
indexing and lists, plus these functions:

| function | meaning |
|---|---|
| `idx('table', value)` | position of `value` in a list table |
| `tbl('table', key)` | entry of a dict table (keys are strings) |
| `min`, `max`, `sum` | as in Python |

Anything else is rejected, so profiles cannot run arbitrary code.

## Tests

For each profile add `tests/fixtures/<id>/manifest.json`:

```json
{ "dpi_1600": { "action": "config", "params": { "dpi1": 1600 } },
  "other":    { "action": "effect", "params": { "mode": "neon" }, "skip_head": 30 } }
```

and a `<name>.seq` next to it with the frames captured from the wire (one per line). `skip_head` drops
leading frames in the capture that are not part of the action.
