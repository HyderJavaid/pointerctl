# Packaging

| Format | Status | How |
|---|---|---|
| `.deb` (Debian, Ubuntu, Mint) | built and tested here | `./packaging/build-deb.sh` -> `dist/pointerctl_<version>_all.deb`; installs the udev rule |
| Python wheel / sdist | built and tested here | `python3 -m pip wheel . --no-deps -w dist` (or `python3 -m build`); `pipx install .` for the command line tool |
| Flatpak | built; GUI and device access verified in the sandbox (`flatpak-builder --run`) | `./packaging/build-flatpak.sh` -> `dist/pointerctl-<version>.flatpak` |
| RPM (Fedora, openSUSE) | **untested** recipe | `packaging/rpm/pointerctl.spec` |
| Arch | **untested** recipe | `packaging/arch/PKGBUILD` |

The program is pure Python, so nothing is compiled; "building" means collecting files.

## Dependencies

Python 3.9+, PyGObject, GTK 4 and libadwaita 1.4+ for the window (`pointerctl-gui`). The command line tool (`pointerctl`) needs only Python.

## The udev rule

Every package must make the rule `udev/70-pointerctl.rules` reach `/usr/lib/udev/rules.d/` (the `.deb` and the recipes do).
Flatpak cannot install it: run `udev/install.sh` once on the host, or install the `.deb`/distribution package.

## Flatpak notes

- Build it with `./packaging/build-flatpak.sh` (needs `flatpak-builder` and the GNOME 50 SDK: `flatpak install flathub org.gnome.Sdk//50`).
- Verified: the sandbox lists the mouse and opens its configuration node read/write, and the window renders. The bundle was not installed with
  `flatpak install` on the author's machine; do that with `flatpak install --user dist/pointerctl-<version>.flatpak`.
- It needs `--device=all` because the mouse is a hidraw device node; the host udev rule still decides whether your user may open it.
- The app id `io.github.naoomeow.Pointerctl` follows Flathub's convention for GitHub projects (`io.github.<account>.<App>`). If the GitHub
  account is ever renamed, change it everywhere (desktop file name, metainfo, icon file name, Flatpak manifest, `APP_ID` in
  `pointerctl/gui/app.py`, tests).
