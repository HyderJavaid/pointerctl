"""pointerctl-gui: a native window that edits a profile's parameters and sends them to the mouse."""
import json
import os
import sys
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gio, Gtk  # noqa: E402

from .. import __version__, device, profiles  # noqa: E402
from ..engine import ProfileError  # noqa: E402

APP_ID = "io.github.naoomeow.Pointerctl"
SHORTCUT = "shortcut:"
SHORTCUT_LABEL = "Keyboard shortcut…"


def pretty(text):
    return str(text).replace("-", " ").capitalize()


class Field:
    """One parameter: knows its spec, current value, and how to build its row."""

    def __init__(self, name, spec, tables, value, on_change):
        self.name, self.spec, self.on_change = name, spec, on_change
        self.value = value
        self.title = spec.get("label", pretty(name))
        self.subtitle = spec.get("description", "")
        self.choices = None
        if spec.get("type") == "choice":
            self.choices = spec.get("choices") or tables[spec["choices_from"]]
        self.shortcut_ok = SHORTCUT in spec.get("allow_prefix", [])
        self.entry = None

    def _label(self, choice):
        labels, unit = self.spec.get("labels", {}), self.spec.get("unit")
        if str(choice) in labels:
            return labels[str(choice)]
        return "%s %s" % (choice, unit) if unit else (pretty(choice) if isinstance(choice, str) else str(choice))

    def rows(self):
        s = self.spec
        if self.choices is not None:
            labels = [self._label(c) for c in self.choices] + ([SHORTCUT_LABEL] if self.shortcut_ok else [])
            row = Adw.ComboRow(title=self.title, subtitle=self.subtitle, model=Gtk.StringList.new(labels))
            is_shortcut = isinstance(self.value, str) and self.value.startswith(SHORTCUT)
            row.set_selected(len(self.choices) if is_shortcut else self.choices.index(self.value))
            row.connect("notify::selected", self._combo_changed)
            self.combo = row
            if not self.shortcut_ok:
                return [row]
            self.entry = Adw.EntryRow(title="Shortcut, for example ctrl+c or alt+tab",
                                      text=self.value[len(SHORTCUT):] if is_shortcut else "")
            self.entry.set_visible(is_shortcut)
            self.entry.connect("changed", self._entry_changed)
            return [row, self.entry]
        if s.get("min") == 0 and s.get("max") == 1:
            row = Adw.SwitchRow(title=self.title, subtitle=self.subtitle, active=bool(self.value))
            row.connect("notify::active", lambda r, _p: self._set(int(r.get_active())))
            return [row]
        adj = Gtk.Adjustment(value=self.value, lower=s["min"], upper=s["max"], step_increment=1, page_increment=10)
        row = Adw.SpinRow(title=self.title, subtitle=self.subtitle, adjustment=adj)
        row.connect("notify::value", lambda r, _p: self._set(int(r.get_value())))
        return [row]

    def _set(self, value):
        self.value = value
        self.on_change()

    def _combo_changed(self, row, _p):
        i = row.get_selected()
        if i >= len(self.choices):                                   # "Keyboard shortcut…"
            self.entry.set_visible(True)
            self._set(SHORTCUT + self.entry.get_text().strip())
        else:
            if self.entry:
                self.entry.set_visible(False)
            self._set(self.choices[i])

    def _entry_changed(self, entry):
        self._set(SHORTCUT + entry.get_text().strip())


class Window(Adw.ApplicationWindow):
    def __init__(self, app, profile):
        super().__init__(application=app, title="Pointerctl", default_width=680, default_height=760)
        # our own symbolic icons ship inside the package, so they exist on every desktop theme
        Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).add_search_path(os.path.join(os.path.dirname(__file__), "icons"))
        self.profile = profile
        self.fields = {}                          # action -> {name: Field}
        self.busy = False
        self.saved = self._load_saved()

        self.toasts = Adw.ToastOverlay()
        self.stack = Adw.ViewStack()
        self.banner = Adw.Banner(title="No supported mouse found. Plug it in and check the udev rule (see the README).")
        self.apply_btn = Gtk.Button(label="Apply to mouse")
        self.apply_btn.add_css_class("suggested-action")
        self.apply_btn.connect("clicked", self._apply)
        self.spinner = Gtk.Spinner()

        header = Adw.HeaderBar(title_widget=Adw.WindowTitle(title="Pointerctl", subtitle=self.profile.name))
        header.pack_start(self.apply_btn)
        header.pack_start(self.spinner)
        menu = Gio.Menu()
        menu.append("About", "app.about")
        header.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu, primary=True))
        bar = Adw.ViewSwitcherBar(stack=self.stack, reveal=True)
        view = Adw.ToolbarView(content=self.stack)
        view.add_top_bar(header)
        view.add_top_bar(self.banner)
        view.add_bottom_bar(bar)
        self.toasts.set_child(view)
        self.set_content(self.toasts)
        self.stack.connect("notify::visible-child", lambda *_: self._refresh())

        for page in self.profile.data.get("ui", {}).get("pages") or self._default_pages():
            self.stack.add_titled_with_icon(self._build_page(page), page["id"], page["title"], page.get("icon", "applications-system-symbolic"))
        GLib.timeout_add_seconds(3, self._poll_device)
        self._poll_device()
        self._refresh()

    # --- profile -> pages
    def _default_pages(self):
        return [{"id": a, "title": pretty(a), "action": a, "groups": [{"title": "", "fields": list(s["fields"])}]}
                for a, s in self.profile.actions.items()]

    def _build_page(self, page):
        action = page["action"]
        specs = self.profile.params(action)
        flds = self.fields.setdefault(action, {})
        pp = Adw.PreferencesPage()
        for g in page["groups"]:
            grp = Adw.PreferencesGroup(title=g.get("title", ""), description=g.get("description", ""))
            for name in g["fields"]:
                if name not in flds:
                    flds[name] = Field(name, specs[name], self.profile.tables, specs[name]["default"], self._refresh)
                    flds[name].value = self._saved_value(action, name, flds[name])
                for row in flds[name].rows():
                    grp.add(row)
            pp.add(grp)
        pp.action = action
        return pp

    def _saved_value(self, action, name, field):
        """Last applied value if it is still valid for this profile, else the default."""
        value = self.saved.get(action, {}).get(name, field.spec["default"])
        if field.choices is None:
            return value if isinstance(value, int) else field.spec["default"]
        if value in field.choices or (field.shortcut_ok and isinstance(value, str) and value.startswith(SHORTCUT)):
            return value
        return field.spec["default"]

    def _current_action(self):
        page = self.stack.get_visible_child()
        return getattr(page, "action", None)

    # --- state
    def _values(self, action):
        return {n: f.value for n, f in self.fields[action].items()}

    def _refresh(self):
        action = self._current_action()
        ok = action is not None and not self.busy and self.device_ok
        self.apply_btn.set_sensitive(bool(ok))
        self.apply_btn.set_tooltip_text(None if ok else "Plug in a supported mouse first" if not self.device_ok else None)

    device_ok = False

    def _poll_device(self):
        try:
            device.find_nodes(self.profile)
            self.device_ok = True
        except device.DeviceError:
            self.device_ok = False
        self.banner.set_revealed(not self.device_ok)
        self._refresh()
        return True

    def _toast(self, text):
        self.toasts.add_toast(Adw.Toast(title=text, timeout=4))

    # --- apply
    def _apply(self, _btn):
        action = self._current_action()
        values = self._values(action)
        try:
            frames = self.profile.build(action, values)
        except ProfileError as e:
            self._toast(str(e))
            return
        self.busy = True
        self.spinner.start()
        self._refresh()
        threading.Thread(target=self._send, args=(action, values, frames), daemon=True).start()

    def _send(self, action, values, frames):
        try:
            device.send(self.profile, frames)
            err = None
        except (device.DeviceError, OSError) as e:
            err = str(e)
        GLib.idle_add(self._done, action, values, err)

    def _done(self, action, values, err):
        self.busy = False
        self.spinner.stop()
        if err:
            self._toast("Could not send: " + err)
        else:
            self._save(action, values)
            self._toast("Applied to the mouse")
        self._refresh()
        return False

    # --- remember what was applied (the mouse cannot be read back)
    def _path(self):
        return os.path.join(GLib.get_user_config_dir(), "pointerctl", "%s-ui.json" % self.profile.id)

    def _load_saved(self):
        try:
            with open(self._path()) as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _save(self, action, values):
        self.saved[action] = values
        try:
            os.makedirs(os.path.dirname(self._path()), exist_ok=True)
            with open(self._path(), "w") as f:
                json.dump(self.saved, f, indent=1)
        except OSError:
            pass


class App(Adw.Application):
    def __init__(self, profile_id=None, page=None):
        super().__init__(application_id=APP_ID)
        self.profile_id, self.page = profile_id, page
        about = Gio.SimpleAction.new("about", None)
        about.connect("activate", self._about)
        self.add_action(about)

    def do_activate(self):
        win = self.get_active_window()
        if not win:
            try:
                profile = self._pick_profile()
            except ProfileError as e:
                print("pointerctl-gui:", e, file=sys.stderr)
                self.quit()
                return
            win = Window(self, profile)
            if self.page:
                win.stack.set_visible_child_name(self.page)
        win.present()

    def _pick_profile(self):
        if self.profile_id:
            return profiles.load(self.profile_id)
        devs = device.hidraw_devices()
        allp = profiles.all_profiles()
        for p in allp.values():
            if any(device.matches(p, d) for d in devs):
                return p
        if allp:                                          # nothing connected: open the first profile so the window explains what is missing
            return next(iter(allp.values()))
        raise ProfileError("no device profiles installed")

    def _about(self, *_):
        dlg = Adw.AboutDialog(application_name="Pointerctl", version=__version__, developer_name="pointerctl contributors",
                              license_type=Gtk.License.MIT_X11, website="https://github.com/naOomeow/pointerctl",
                              comments="Unofficial settings tool for mice. Not affiliated with or endorsed by any manufacturer.")
        dlg.present(self.get_active_window())


def main(argv=None):
    argv = sys.argv if argv is None else argv
    opt = lambda name: argv[argv.index(name) + 1] if name in argv else None  # noqa: E731
    return App(opt("--profile"), opt("--page")).run([argv[0]])


if __name__ == "__main__":
    raise SystemExit(main())
