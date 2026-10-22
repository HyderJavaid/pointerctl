# GM21 protocol notes

Everything here was derived mainly from USB captures of the manufacturer's configuration software talking to one GM21
(`30fa:1441`), and checked against the real mouse. "Verified" means reproduced byte for byte from a capture;
"confirmed on hardware" means the effect was observed on the mouse. Unknowns are listed at the end.

## Transport

- The mouse has two HID interfaces. Interface 0 is the pointer (report 1: buttons, 16-bit x, 16-bit y, wheel).
  Interface 1 contains keyboard (3), consumer (2) and vendor-defined collections, including a vendor feature report
  **id 7** (usage page `0xFF01`, 7 data bytes) that is the configuration channel.
- All configuration is **HID feature reports of 8 bytes** (`07` + 7 data bytes) sent with SET_FEATURE to interface 1
  (on Linux: `HIDIOCSFEATURE` on the hidraw node whose descriptor contains `06 01 ff`).
- On the wire the frames are spaced about 2-3 ms apart, 8-9 ms after commit frames, with a GET_FEATURE after read
  frames. The tool copies this pacing.
- Button events (for example the DPI button) arrive as input report 6: `06 f6 00` on press and `06 f6 80` on release.
  They do not say which DPI level is active, and the mouse cannot be asked for it.

## Frame types

`07 18 03 <idx> <base> <bank> <value> <len-1>` writes **one byte** of the mouse's configuration memory:
the address is (`bank`, `base`, `idx`) and `len-1` is the length of the block it belongs to minus one (`17` = 24 bytes,
`1f` = 32 bytes, `07` = 8 bytes). A block is followed by commit frames `07 18 09 00 <base> ...` and `07 18 00 00 <base> ...`.
`07 18 05 <idx> <base> ...` reads a byte back. `07 18 10 ...` ends a full dump. `07 13 ff <mode> <b> <x> 3f ff` is an
"apply" frame of the colour and effect bursts.

## Two kinds of traffic

1. **Full configuration (727 frames)**, sent when the configuration is applied (DPI, polling, button, on-device lighting
   settings). It rewrites memory pages `0x20`-`0xe0` (32 bytes each, in banks 0-2, mostly zero), a 24-byte block at base
   `0x08`, and single bytes at `0x01` and `0x7f`. The settings below live in block `0x08` and page `0x20`.
2. **Colour and effect bursts**: five state blocks followed by five apply blocks, 215 frames for most effects (305 for a
   solid colour, 430 for the comet effect, 200 for off). Switching effects first re-sends an apply block for the previous
   effect, which the tool omits.

## Settings in the full configuration (verified)

Addresses are written as base/idx; all frames are `07 18 03 <idx> <base> 00 <value> <len-1>`.

| Setting | Where | Encoding |
|---|---|---|
| DPI level n (1-6) | block `0x08` idx 13-15 (low nibbles), idx 11 (bit 4) | each level has a 5-bit *step*; low 4 bits go in a nibble (L1/L2 in idx 13, L3/L4 in idx 14, L5/L6 in idx 15, odd level in the high nibble), bit 4 of level n is bit n-1 of idx 11 |
| step to DPI | table | steps 1-10: 200 x step; 11: 2400; 12-22: 3200 + 800 x (step-12); 23: 12800 |
| selected DPI level | `0x08` idx 16 | `7 + level` |
| DPI levels enabled | `0x08` idx 17 | bit n-1 = level n on (`3f` = all six) |
| button debounce time | `0x08` idx 18 | `ms // 8` (19 to 300 ms seen) |
| polling rate | `0x08` idx 22 | interval in ms minus 1: 1000 Hz `00`, 500 `01`, 250 `03`, 125 `07` |
| rate flag | `0x20` idx 26 low nibble | `0a` at 500 Hz, `09` otherwise (purpose unknown) |
| on-device LED brightness | `0x20` idx 31 | `(7 - brightness) * 16` |
| on-device LED speed | `0x08` idx 20 low nibble | `speed - 1` |
| LED symmetry / direction | `0x20` idx 26 | bit 6 / bit 4 |
| on-device LED mode | `0x08` idx 20 high nibble, `0x20` idx 19 | list index m: nibble `8 + (m & 7)`, idx 19 = `ff` if m >= 8 else `7f`; mode 12 = idx 20 `99`, idx 19 `7f`; off = idx 20 `87`, idx 19 `ff` |

Mode order (m = 0..13): dpi-breathing, cycle-breath, always-bright, flowing-water, mono-water, comet-tail, neon, ambient,
flashing, effect-9, ripple, effect-11, effect-12, led-off. "effect-N" modes were captured but their look was not characterised.

The firmware loads a level's DPI when the selected level changes or the DPI button is pressed. Rewriting the same selected
level leaves the old DPI active until the next press (observed with pointer-count measurements; not proven).
Confirmed on hardware: polling rate (125 Hz measured 125 reports/s, 1000 Hz measured 985), DPI levels, disabled levels
being skipped, LED off, a visible change for the ripple mode.

## Buttons (verified, buttons 2-7)

Seven buttons, each stored as one byte in block `0x08`: button 1 -> idx 0 (left click, left fixed), 2 -> idx 1,
3 -> idx 2, 4 -> idx 4, 5 -> idx 3, 6 -> idx 7, 7 -> idx 5. idx 6 is unused. Value = `0x20 | code` (button 6 / idx 7 has no `0x20`).
Function codes: 0 none, 1 left, 2 middle, 3 right, 4 backward, 5 forward, 7 show desktop, 8 double click, 9 fire,
`b` DPI+, `c` DPI-, `f` media key, `d` keyboard shortcut. Defaults: left, middle, right, forward (btn 4), backward (btn 5),
DPI+ (btn 6), DPI- (btn 7).

A **media key** uses code `f` and a 10-byte entry in a side table made of pages `0xa0`, `0xc0` and `0xe0` (bank 0) read as one
96-byte region: the entry of the button with block index k starts at offset `3 + 10k` and holds the HID consumer-control usage
(little-endian 16 bits: Play/Pause `0xcd`, Volume Up `0xe9`, Mute `0xe2`, Next Track `0xb5`, Stop `0xb7`, Calculator `0x0192`)
followed by one unknown byte and `04` at +3. Non-media entries are zero. Confirmed on hardware: Calculator on button 7.

**Keyboard shortcuts** (`<modifier>+<key>`, verified against captures of Copy, Paste, Undo and Select All; button byte `0x2d`, or `0x0d`
for button 6) are stored as a small macro:

- **Event list**, 12 bytes per shortcut, in memory bank 4 starting at base 0, macros stored back to back in button-index order:
  `01 00 | (d1+1) mod | 7f 00 | (d2|0x80) key | d3 key | d4 mod`. `mod` is the HID modifier usage (`e0` Ctrl, `e1` Shift, `e2` Alt, `e3` Win)
  and `key` the HID keyboard usage (C = `06`). `d1..d4` are four delays; the four captured shortcuts carry their own values,
  e.g. Copy 223/90/38/20. Frames are written like any block (`07 18 03 <idx> <base> 04 <value> <len-1>`, 32 bytes per block, with
  commit frames) just before the final `07 18 10` frame of the full dump.
- **Side-table entry** of the button (offset `10k`): +1 = number of key events (5), +5 = start offset of its macro, +6 = `04`, +8 = byte length (10).
  Entries of the other buttons get +5 = total macro bytes of the buttons before them (index order).
- **Pointer page** `0x60` idx 14, 16, 18, 20, 25 = `T, T+8, T+16, T+24, T+32` where `T` is the total macro bytes (0 when there are none);
  they point to four 8-byte user-macro slots behind the shortcut macros.

Shortcuts with other keys use default delays (160/100/30/20); Alt+Tab with those delays was confirmed on hardware.
Recorded multi-event macros and shortcuts with more than one modifier are not decoded.

## Colour and effect bursts (verified)

**These writes are non-volatile.** Confirmed on hardware: after sending a solid colour (cyan) and unplugging and replugging the mouse, it
came back cyan, not with its previous lighting. So a colour or effect burst is a permanent write, the same as a configuration. The
endurance of that memory is unknown, and each burst writes the same pages five times, so never send them repeatedly (no animation,
audio-reactive or timer-driven lighting from the computer).

- Effect codes (bank `0x1c` idx 0 and the `07 13` apply frames): constant `a`, breath `9`, flowing water `b`,
  single LED `c`, comet `d`, neon `e`, ambient `f` in the high nibble; low nibble = `frequency - 1` (frequency 1-6, default 3).
  Off uses `f7` and sends no apply frames.
- Brightness b: last apply frame of each block has `7 - b`, and bank `0x3e` idx 1 = `(7 - b) * 16`.
- Solid colour: bank `0x20` idx 3-5 = `0xf0 | (15 - R)`, `0xb0 | (15 - G)`, `15 - B` with 4-bit channels
  (yellow F F 0, red F 0 0, green 3 E 0, blue 0 4 F, magenta F 0 D, cyan 0 E E, white F F F). Only one colour is sent for the
  solid effect. The meaning of those bytes in the animated effects is not decoded.

## Unknown / not decoded

- Recorded macros and multi-modifier shortcuts (see Buttons), and any further button function categories.
- Colour selection in animated effects; what bank `0x28`/`0x30`/`0x3a` values mean (replayed as captured).
- The `0x3a` byte that differs between the five state blocks of a burst (replayed as captured).
- Whether other models (GM19/20/23/31) use the same layout.
