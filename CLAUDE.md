# Instructions for AI assistants working on pointerctl

This file is read automatically by Claude Code and is meant for any AI coding assistant. A human maintainer or contributor
is in charge; you assist.

## What this project is

pointerctl configures mice on Linux over `hidraw` (unofficial, MIT licensed). A mouse is described by a **profile**
(`pointerctl/profiles/<id>/profile.json` plus template frame files). The engine (`pointerctl/engine.py`) is generic; a GUI
is generated from the profile. Read `README.md`, `CONTRIBUTING.md`, `docs/profile-format.md`, `docs/adding-a-mouse.md` and
`docs/protocol-gm21.md` before changing anything. Run the tests with `python3 -m unittest discover -s tests -v`.

## Safety rules (hardware)

- **Never write to a device without the user's explicit approval for that specific write.** Dry runs (no `--yes`) are fine.
  Read-only commands (`identify`, `list`, `diag`) are fine.
- **Writes are permanent.** A solid colour survived unplugging the mouse, so every write (colour and effect bursts included) goes to
  non-volatile memory of unknown endurance. Never put writes in a loop or stream them (animations, visualisers, timers, polling
  automation); one write per deliberate user action, and tell the user about the wear risk if they ask for anything repeated.
- Only send frames that exist in a capture, or a captured frame with a value changed where a capture or an objective measurement
  shows what that value does. Never send guessed or unknown frames. Never write firmware.
- Verify effects objectively where possible (`pointerctl diag measure` for polling rate, `diag counts` for DPI) and report
  honestly what you could not verify. Do not claim something works that was not tested.
- Other models share USB ids with the GM21. Do not bypass the model check (`POINTERCTL_FORCE`) on the user's behalf.

## Legal hygiene (this matters)

- **Work black-box.** Derive everything from USB traffic captures and from observing the device itself. Do not decompile, disassemble or
  read the manufacturer's program, installer or its data files (not even "just to cross-check"). If a user hands you such files, say you
  won't use them.
- **Describe the method accurately.** Do not call this project "clean-room" in any text you write; it is not a formal clean-room process.
  Say what was actually done: captures of the manufacturer's software talking to the user's own mouse, for interoperability.
- Your job with a user's own captures (a private `captures/` folder, never committed) is to analyse them. "Private" means "don't
  commit or publish", not "don't read".

- **Never add** manufacturer software, libraries, images, text, config/language/JSON/INI files, decompiled or disassembled code,
  or anything copied from them. Describe behaviour in your own words ("report 7, byte 13 = DPI step").
- **Never commit raw captures** (`.pcapng`) or anything with serial numbers. Commit extracted frame lists (`.seq`) only.
- Do not reuse the manufacturer's UI wording or marketing names for modes and functions; choose neutral names. "Meetion GM21" may
  appear only to name supported hardware.
- Before every commit run `git status` and check that no build output (`dist/`, `build/`, `*.egg-info`, `.flatpak-builder/`),
  captures, or vendor files are staged.

## How to add a mouse (summary of docs/adding-a-mouse.md)

1. `python3 -m pointerctl identify`: note vid:pid, name, descriptor; find the vendor feature-report interface.
2. The user captures traffic one setting at a time with `tools/capture.sh` (baseline first). Diff with `tools/capture_diff.py`.
3. Work out the encoding from several data points (min, middle, max); check for tables, nibble packing, shared bytes, checksums.
4. Write `profile.json` (fields, tables, patches) and the template frame files. Add `tests/fixtures/<id>/` with a manifest and
   one `.seq` per verified capture; the tests must rebuild each byte for byte.
5. Add a `ui` layout so the GUI shows the settings. Dry-run first, then ask the user to approve each real write.

## Code style

Standard library only, Python 3.9+. Keep the engine small and put mouse specifics in profile data. If you need a new capability,
extend the expression language or the patch format rather than adding mouse-specific Python. Every behaviour needs a test.

## Finishing

Before saying a task is done, run `python3 -m unittest discover -s tests -v` and report the result.

Summarise what you changed, what you verified on hardware and how, and what remains untested or unknown.
