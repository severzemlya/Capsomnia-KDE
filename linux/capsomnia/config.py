"""User preferences and crash-recovery state.

Two files under ~/.config/capsomnia/:
  - config.ini : user-visible preferences (language, tray, autostart, lid display-off)
  - state.ini  : runtime recovery state. If Capsomnia is killed while Caps Lock is
                 on, the saved PowerDevil LidAction values live here so the next
                 launch can restore normal sleep behavior.
"""

from __future__ import annotations

import configparser
import os
from pathlib import Path


def _config_home() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "capsomnia"


CONFIG_DIR = _config_home()
CONFIG_PATH = CONFIG_DIR / "config.ini"
STATE_PATH = CONFIG_DIR / "state.ini"

# Sentinel meaning "the key was absent in powerdevilrc" — restore by deleting it.
ABSENT = "__absent__"


def _default_language() -> str:
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "")
        if value.startswith("ja"):
            return "ja"
    return "en"


class Preferences:
    """User-visible preferences, persisted to config.ini."""

    def __init__(self) -> None:
        self._parser = configparser.ConfigParser()
        self._parser.read(CONFIG_PATH, encoding="utf-8")
        if "general" not in self._parser:
            self._parser["general"] = {}
        self._g = self._parser["general"]
        self._g.setdefault("language", _default_language())
        self._g.setdefault("show_tray_icon", "true")
        self._g.setdefault("launch_at_login", "true")
        self._g.setdefault("display_off_on_lid_close", "false")

    # --- typed accessors -------------------------------------------------
    @property
    def language(self) -> str:
        return self._g.get("language", "en")

    @language.setter
    def language(self, value: str) -> None:
        self._g["language"] = value
        self.save()

    @property
    def show_tray_icon(self) -> bool:
        return self._g.getboolean("show_tray_icon", True)

    @show_tray_icon.setter
    def show_tray_icon(self, value: bool) -> None:
        self._g["show_tray_icon"] = "true" if value else "false"
        self.save()

    @property
    def launch_at_login(self) -> bool:
        return self._g.getboolean("launch_at_login", True)

    @launch_at_login.setter
    def launch_at_login(self, value: bool) -> None:
        self._g["launch_at_login"] = "true" if value else "false"
        self.save()

    @property
    def display_off_on_lid_close(self) -> bool:
        return self._g.getboolean("display_off_on_lid_close", False)

    @display_off_on_lid_close.setter
    def display_off_on_lid_close(self, value: bool) -> None:
        self._g["display_off_on_lid_close"] = "true" if value else "false"
        self.save()

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
            self._parser.write(fh)


class RecoveryState:
    """Runtime recovery state, persisted to state.ini.

    Holds the PowerDevil LidAction values that were in effect before Capsomnia
    overrode them, keyed by profile (AC/Battery/LowBattery). Present only while
    Capsomnia is actively suppressing sleep.
    """

    SECTION = "powerdevil_lid"

    def __init__(self) -> None:
        self._parser = configparser.ConfigParser()
        self._parser.read(STATE_PATH, encoding="utf-8")

    def has_saved_lid_actions(self) -> bool:
        return self._parser.has_section(self.SECTION) and bool(
            self._parser[self.SECTION]
        )

    def saved_lid_actions(self) -> dict[str, str]:
        if not self._parser.has_section(self.SECTION):
            return {}
        return dict(self._parser[self.SECTION])

    def save_lid_actions(self, actions: dict[str, str]) -> None:
        self._parser[self.SECTION] = dict(actions)
        self._write()

    def clear_lid_actions(self) -> None:
        if self._parser.has_section(self.SECTION):
            self._parser.remove_section(self.SECTION)
        self._write()

    def _write(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(STATE_PATH, "w", encoding="utf-8") as fh:
            self._parser.write(fh)
