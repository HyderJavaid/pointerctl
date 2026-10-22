# Contributing

Thanks for helping! The most valuable contributions are **profiles for more mice** and **more decoded settings**.

## What must never be committed

This project describes a device protocol for interoperability; it does not redistribute vendor material. It is not a formal
"clean-room" project, so please don't describe it as one.

- No vendor executables, DLLs, installers, images, skins, or their configuration/language/JSON/INI files.
- No decompiled or disassembled code, and no code or text copied from vendor software.
- No raw captures (`.pcapng`): they can contain serial numbers. Commit the extracted frame lists (`.seq`) instead.
- Describe behaviour in your own words ("report 7, byte 13 = DPI step"), not by pasting vendor structures.

`.gitignore` blocks the obvious ones. Check `git status` before committing.

## Safety rules for protocol work

- Only send frames that are in your captures, or patterns that are a captured frame with a value changed
  where you have shown (by a capture or an objective measurement) what that value does.
- Never send unknown frames to a mouse, and never write firmware. Be careful with pages of memory you don't understand.
- Verify on hardware with something objective where you can (`pointerctl diag measure` for polling rate, `diag counts`
  for DPI). "It felt faster" is a hint, not a proof.

## Adding or changing a profile

1. Follow [docs/adding-a-mouse.md](docs/adding-a-mouse.md).
2. Add the frame lists you rebuilt as fixtures: `tests/fixtures/<id>/<name>.seq` and an entry in
   `tests/fixtures/<id>/manifest.json` (action + parameters).
3. `python3 -m unittest discover -s tests` must pass.
4. In the pull request say: the exact model and USB id (`pointerctl identify`), what you tested on real hardware and how,
   and what you could not test.

## Code

Standard library only, Python 3.9+. Keep the engine small and the profiles as data. If you need a new capability,
prefer extending the expression language or patch format over adding mouse-specific Python.

## Bug reports

Please include `python3 -m pointerctl identify` output (it is read-only), your distro, and the command you ran.
