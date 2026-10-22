# Changelog

## 0.1.0

First release.

- Meetion GM21 profile: six DPI levels (with per-level on/off and selected level), polling rate, button debounce time,
  button functions for buttons 2-7 (mouse functions, media keys, `<modifier>+<key>` keyboard shortcuts), on-device
  lighting (14 modes, brightness, speed, symmetry, direction), live colour and animated effects.
- Command line tool (`pointerctl`) with dry run by default, and a GTK4/libadwaita window generated from the profile.
- Profile-driven engine: new mice are added as data (see docs/adding-a-mouse.md).
- Packages: `.deb`, wheel, Flatpak (RPM and Arch recipes untested).
- Colour and effect writes are stored in the mouse's permanent memory (a solid colour survived unplugging it), so they are not "live";
  do not call them in a loop (see the README safety note).
- Known gaps: recorded macros, multi-modifier shortcuts, colour choice in animated effects, other models.
