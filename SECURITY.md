# Security

pointerctl writes configuration to USB devices you own and, for keyboard shortcuts on buttons, can make a mouse button
type keys. Please report problems privately (a GitHub security advisory on this repository) instead of a public issue if you find:

- a way for a profile file to run code or write outside the intended device frames,
- a frame sequence that bricks or misconfigures a device beyond its factory reset,
- a flaw in the udev rule or packaging that gives users more device access than intended.

Profiles are data. The expression language is a small whitelist (no attribute access, calls only to a few helpers), and
a profile can only make the tool send HID feature reports to the device the profile matches. Treat a profile from a stranger
like a configuration file, not like a program, and read it before using it.
