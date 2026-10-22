# Release checklist

Work through this top to bottom. Items marked (you) need a decision or an account that only the maintainer has.

## Before the first public release

- [x] Public identity set to the GitHub username and no-reply address. Original item: pick the public identity for commits: `git config user.name` / `user.email` (a GitHub noreply address is fine),
      then check `git log --format='%an <%ae>'`. If the existing commit shows a placeholder, recreate it: `git commit --amend --reset-author`.
- [x] GitHub account `naOomeow`; placeholders replaced. Original item: create the GitHub account or organisation, then replace the placeholders everywhere:
      `github.com/naOomeow/pointerctl` (README, `packaging/`), the app id `io.github.naoomeow.Pointerctl`
      (desktop file, metainfo, icon file name, Flatpak manifest, `APP_ID` in `pointerctl/gui/app.py`, tests) and the developer id in the metainfo.
- [ ] (you) Search for the name "pointerctl" (web, GitHub, trademark databases for your country) and confirm you are comfortable with it.
- [ ] (you) Have someone qualified read the legal wording in the README and CONTRIBUTING.md (interoperability, no manufacturer
      software or assets, nominative use of the hardware name). This project cannot give legal advice.
- [x] `.deb` install test done on Linux Mint 22.3 (the author's machine): installs, launchers and menu entry work, the package's udev rule alone
      grants access (verified with the manual rule moved aside), CLI and GUI both wrote to a real GM21, removal leaves 0 of 33 files behind,
      reinstall works. Still worth repeating on a clean VM and on Ubuntu/Debian, which the author did not test.
- [ ] (you) Install the Flatpak: `flatpak install --user dist/pointerctl-0.1.0.flatpak`, run it, apply once. The host needs the udev rule (`udev/install.sh`).
- [ ] (you) Test on every other supported model you can borrow, or say clearly which are untested (the README table does).
- [x] Screenshots added in `docs/screenshots/` and referenced in the metainfo (the links work once the repository is public on branch `main`).
- [ ] Remove the old manual udev rule on your own machine if you installed it earlier: `/etc/udev/rules.d/70-meetion.rules`.

- [x] Private vulnerability reporting enabled on the repository (Settings > Code security), so the link in SECURITY.md works.

## Checks that can be repeated (already green at the time of writing)

- [ ] `python3 -m unittest discover -s tests -v` passes (also with a display, so the GUI tests run).
- [ ] Fresh clone builds: `git clone . /tmp/x && cd /tmp/x && ./packaging/build-deb.sh`, wheel and Flatpak the same way.
- [ ] No manufacturer files or captures tracked: `git ls-files | grep -Ei '\.(exe|dll|pcapng|ini)$'` prints nothing.
- [ ] No personal data: `git grep -n -I -i -E 'your-name|your-email|/home/'` prints nothing.
- [ ] `git grep -n -i meetion -- . ':!tests/fixtures'` shows only factual hardware-compatibility mentions.
- [ ] `desktop-file-validate`, `appstreamcli validate --no-net` and `udevadm verify udev/*.rules` pass.
- [ ] The wheel and packages contain no stale files (inspect with `unzip -l` / `dpkg-deb --contents`; delete `build/` and `*.egg-info` first).

## Release

- [ ] Update the version in `pointerctl/__init__.py`, `pyproject.toml`, the metainfo `<release>` entry, `CHANGELOG.md` and the RPM spec.
- [x] Tagged and pushed v0.1.0 (annotated tag). Original item: tag with `git tag -a v0.1.0 -m "pointerctl 0.1.0"` and push the tag.
- [x] v0.1.0 release published with the `.deb`, wheel, `.flatpak` and `SHA256SUMS` attached; downloads verified against the sums.
- [ ] Optional: publish to PyPI (`python3 -m build && twine upload dist/*`), submit the Flatpak to Flathub, open a Debian/Ubuntu PPA.

## After release

- [ ] Watch the new-device issues; ask for `pointerctl identify` output and never ask anyone to run a write they do not understand.
- [ ] Keep the private research material (captures, vendor files) out of every public place.
