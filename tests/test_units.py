"""Lightweight, non-destructive unit tests for the KDE port.

Run: python3 -m unittest discover -s linux/tests
(These avoid touching PowerDevil or logind — those paths are exercised
end-to-end during install verification, see linux/README.md.)
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class CapsLockParsingTests(unittest.TestCase):
    def test_read_from_sysfs_like_tree(self):
        import capsomnia.capslock as capslock

        with tempfile.TemporaryDirectory() as tmp:
            led_a = Path(tmp) / "input3::capslock" / "brightness"
            led_a.parent.mkdir(parents=True)
            led_a.write_text("1\n")
            capslock._LED_GLOB = str(Path(tmp) / "*capslock*" / "brightness")
            self.assertTrue(capslock.read_capslock())
            led_a.write_text("0\n")
            self.assertFalse(capslock.read_capslock())

    def test_none_when_no_led(self):
        import capsomnia.capslock as capslock

        capslock._LED_GLOB = "/nonexistent/*/brightness"
        self.assertIsNone(capslock.read_capslock())


class RecoveryStateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["XDG_CONFIG_HOME"] = self._tmp.name
        # Re-import config with the patched env.
        for mod in ("capsomnia.config",):
            sys.modules.pop(mod, None)

    def tearDown(self):
        self._tmp.cleanup()
        os.environ.pop("XDG_CONFIG_HOME", None)

    def test_lid_action_roundtrip(self):
        import importlib

        import capsomnia.config as config

        importlib.reload(config)
        state = config.RecoveryState()
        self.assertFalse(state.has_saved_lid_actions())
        state.save_lid_actions({"AC": "0", "Battery": config.ABSENT})
        state2 = config.RecoveryState()
        self.assertTrue(state2.has_saved_lid_actions())
        saved = state2.saved_lid_actions()
        # configparser lowercases keys.
        self.assertEqual(saved["ac"], "0")
        self.assertEqual(saved["battery"], config.ABSENT)
        state2.clear_lid_actions()
        self.assertFalse(config.RecoveryState().has_saved_lid_actions())


class I18nTests(unittest.TestCase):
    def test_languages(self):
        import capsomnia.i18n as i18n

        self.assertEqual(i18n.strings("ja").menu_quit, "終了")
        self.assertEqual(i18n.strings("en").menu_quit, "Quit")
        # Unknown falls back to English.
        self.assertEqual(i18n.strings("xx").menu_quit, "Quit")


if __name__ == "__main__":
    unittest.main()
