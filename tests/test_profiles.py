"""Every fixture is a sequence of frames captured from a real GM21; the engine must reproduce it byte for byte.

Run from the repo root:  python3 -m unittest discover -s tests -v
"""
import json
import os
import unittest

from pointerctl import engine, profiles

HERE = os.path.dirname(os.path.abspath(__file__))


def load_profile_cases():
    """Yield (profile id, fixture dir) for every tests/fixtures/<profile-id>/manifest.json."""
    root = os.path.join(HERE, "fixtures")
    for pid in sorted(os.listdir(root)):
        if os.path.exists(os.path.join(root, pid, "manifest.json")):
            yield pid, os.path.join(root, pid)


class FixtureTests(unittest.TestCase):
    def test_all_fixtures(self):
        n = 0
        for pid, fdir in load_profile_cases():
            profile = profiles.load(pid)
            with open(os.path.join(fdir, "manifest.json")) as f:
                manifest = json.load(f)
            for name, case in manifest.items():
                with open(os.path.join(fdir, name + ".seq")) as f:
                    want = f.read().split()[case.get("skip_head", 0):]
                with self.subTest(profile=pid, fixture=name):
                    self.assertEqual(profile.build(case["action"], case["params"]), want)
                n += 1
        self.assertGreater(n, 0, "no fixtures found")


class EngineTests(unittest.TestCase):
    def test_expressions(self):
        self.assertEqual(engine.evaluate("(a + 1) * 16 if a < 3 else 0", {"a": 2}), 48)
        self.assertEqual(engine.evaluate("t[1]", {"t": [5, 6]}), 6)

    def test_expression_rejects_code(self):
        for bad in ("__import__('os')", "open('x')", "(1).__class__", "[x for x in y]", "lambda: 1"):
            with self.assertRaises(engine.ProfileError):
                engine.evaluate(bad, {})

    def test_pattern(self):
        self.assertEqual(engine.parse_pattern("0718030d0800??17")[6], (6, None))
        with self.assertRaises(engine.ProfileError):
            engine.parse_pattern("0718")


class GM21ParameterTests(unittest.TestCase):
    def setUp(self):
        self.p = profiles.load("gm21")

    def test_defaults_equal_template(self):
        self.assertEqual(self.p.build("config"), self.p.template("config.seq"))

    def test_bad_values_are_rejected(self):
        for given in ({"dpi1": 1234}, {"rate": 333}, {"debounce_ms": 5}, {"led_mode": "disco"}, {"nope": 1}):
            with self.assertRaises(engine.ProfileError):
                self.p.build("config", given)

    def test_selected_level_must_be_enabled(self):
        with self.assertRaises(engine.ProfileError):
            self.p.build("config", {"select": 2, "enable2": 0})

    def test_all_levels_off_rejected(self):
        off = {"enable%d" % i: 0 for i in range(1, 7)}
        with self.assertRaises(engine.ProfileError):
            self.p.build("config", dict(off, select=1))


if __name__ == "__main__":
    unittest.main()
