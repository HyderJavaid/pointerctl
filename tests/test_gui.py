"""Drive the generated GUI controls (skipped when GTK4/libadwaita or a display is not available)."""
import os
import unittest

try:
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, Gtk
    HAVE_GTK = Gtk.init_check() and True
except (ImportError, ValueError):
    HAVE_GTK = False


@unittest.skipUnless(HAVE_GTK and (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")), "needs GTK4, libadwaita and a display")
class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pointerctl import profiles
        from pointerctl.gui import app as gui
        cls.gui = gui
        cls.profile = profiles.load("gm21")
        Adw.init()
        cls.app = Adw.Application(application_id="io.github.naoomeow.Test", flags=0)
        cls.app.register(None)
        os.environ["XDG_CONFIG_HOME"] = "/tmp/pointerctl-gui-test"          # never touch the user's saved settings

    def window(self):
        win = self.gui.Window(self.app, self.profile)
        self.addCleanup(win.destroy)
        return win

    def test_every_profile_page_is_built(self):
        win = self.window()
        ids = [p["id"] for p in self.profile.data["ui"]["pages"]]
        self.assertEqual([win.stack.get_page(win.stack.get_child_by_name(i)).get_name() for i in ids], ids)

    def test_defaults_build_valid_frames(self):
        win = self.window()
        for action in win.fields:
            self.assertTrue(self.profile.build(action, win._values(action)))

    def test_choice_row_updates_value(self):
        win = self.window()
        f = win.fields["config"]["dpi1"]
        f.combo.set_selected(f.choices.index(800))
        self.assertEqual(f.value, 800)

    def test_switch_and_spin_rows(self):
        win = self.window()
        f = win.fields["config"]["enable2"]
        f._set(0)
        self.assertEqual(win._values("config")["enable2"], 0)
        self.assertEqual(self.profile.build("config", win._values("config"))[0][:2], "07")

    def test_shortcut_entry(self):
        win = self.window()
        f = win.fields["config"]["button4"]
        f.combo.set_selected(len(f.choices))                 # "Keyboard shortcut…"
        f.entry.set_text("ctrl+c")
        self.assertEqual(f.value, "shortcut:ctrl+c")
        self.assertTrue(self.profile.build("config", win._values("config")))


if __name__ == "__main__":
    unittest.main()
