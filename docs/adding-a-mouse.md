# Adding support for a new mouse

A mouse does not describe its own configuration protocol, so support comes from watching what the manufacturer's
configuration software sends. You need that software running once (on Windows, for example in a VM with USB passthrough)
and a Linux machine to capture the traffic. After that, everyone with the same mouse benefits.

If you're unsure, open an issue first with the output of `python3 -m pointerctl identify` (it only reads).

## 1. Identify the device

```bash
python3 -m pointerctl identify
```

Note the USB id (`vid:pid`), the product name, and the report descriptor. Many models share an id; the name tells
them apart. Look for a vendor-defined interface (usage page `0xFF00`..`0xFFFF`) with a **feature report**: that is
usually the configuration channel. In the GM21 it is report 7, 8 bytes, on the second interface.

## 2. Get the configuration software talking to the mouse

Any way that lets you capture USB traffic works:

- A Windows VM with USB passthrough, capturing on the Linux host with usbmon (USB traffic can also be captured on Windows
  with USBPcap).

## 3. Capture one change at a time

```bash
sudo ./tools/capture.sh baseline      # Ctrl+C to stop; refuses to overwrite existing names
```

Rules that make the decoding easy:

- **Change exactly one setting per capture** (one DPI value, one colour, one toggle), then click apply, wait
  2-3 seconds, stop the capture. Name captures after what you did (`dpi_1600`, `rate_1000`).
- Capture an "apply with no change" first. It shows the software's full dump and gives you a baseline to diff against.
- When a setting has several values, capture at least 3 (for example the minimum, a middle and the maximum) to
  find the pattern. Pick values that differ in as many bits as possible.
- Keep a note of the exact numbers the software shows, since sliders often snap to a table.

## 4. Diff the captures

```bash
python3 tools/capture_diff.py captures/baseline.pcapng captures/dpi_1600.pcapng
python3 tools/capture_diff.py --extract captures/dpi_1600.pcapng > dpi_1600.seq
```

One changed frame usually means one byte for that setting. Typical encodings you will meet: a value divided by a
unit, a lookup table, a nibble packed with another setting, one bit in a shared byte, `max - value`.
Some settings appear in more than one place.

## 5. Write the profile

Create `pointerctl/profiles/<id>/` with:

- `profile.json`: matching, transport, tables, actions, fields and patches (see [profile-format.md](profile-format.md)),
- the template frame lists the actions start from (an extracted capture at default settings).

You can try a profile without installing it by putting it in `~/.config/pointerctl/profiles/<id>/`.

## 6. Prove it

1. Add each capture you rebuilt as `tests/fixtures/<id>/<name>.seq` plus a manifest entry. The tests rebuild every
   fixture from your profile and require identical bytes.
2. Dry-run: `python3 -m pointerctl --profile <id> <action> key=value` builds the frames without sending.
3. On the real mouse, send with `--yes` and check the effect **objectively** where possible
   (`pointerctl diag measure` for polling rate, `pointerctl diag counts` for DPI).
4. Start with settings that are easy to undo. Never send frames or memory pages you do not understand.

## 7. Submit

Open a pull request following [CONTRIBUTING.md](../CONTRIBUTING.md). Say which model and USB id you tested,
what you verified on hardware, and what you could not test.

## Partial support is welcome

You do not have to decode everything. A profile with just the polling rate, or just the DPI levels, is a real improvement and
a good base for others to extend. Say in the pull request what is and isn't covered.

## Using an AI assistant (for example Claude Code)

An assistant can do the tedious parts: diffing captures, spotting encodings, writing the profile and the fixtures, and running the
tests. This repository includes [CLAUDE.md](../CLAUDE.md), which Claude Code reads automatically and which tells it this project's
safety and legal rules. Other assistants can be pointed at the same file.

1. Clone the repository and start the assistant inside the folder.
2. Do the human-only parts yourself: plug in the mouse, run the manufacturer's software (Windows or a VM) and capture the traffic
   with `tools/capture.sh`, **one setting change per capture**, named after what you did.
3. Give it a prompt like this, with your details filled in:

   > I own a <brand and model>, USB id <vid:pid>. I have usbmon captures in `captures/`, one setting changed per capture, named
   > after the change (`dpi_800`, `rate_1000`, ...), plus `baseline` (apply with no change). Read CLAUDE.md and
   > docs/adding-a-mouse.md, then work out which bytes encode each setting, write a profile under `pointerctl/profiles/<id>/`
   > with test fixtures, and run the tests. Don't send anything to the mouse without asking me first, and tell me what you could
   > not verify.

4. Review what it proposes. **You approve every write to the mouse**, and you check each effect yourself, ideally with a
   measurement (`pointerctl diag`) and not by feel.
5. Keep captures and the manufacturer's files out of the repository. The assistant is instructed to, but check `git status` before
   committing.

You remain responsible for what you submit, whether a human or an assistant wrote it.
