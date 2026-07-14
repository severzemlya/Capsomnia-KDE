"""Optional: turn the display off when the lid closes (Caps Lock still on).

Mirrors the macOS app's "display sleep on lid close" option. Watches the ACPI
lid state and, on a closed transition while sleep is being suppressed, blanks
the screen via kscreen-doctor DPMS. Work keeps running; only the panel sleeps.
"""

from __future__ import annotations

import glob
import shutil
import subprocess

_LID_GLOB = "/proc/acpi/button/lid/*/state"


def lid_is_closed() -> bool | None:
    """Return True if the lid is closed, False if open, None if unknown."""
    for path in glob.glob(_LID_GLOB):
        try:
            with open(path, "r", encoding="ascii") as fh:
                contents = fh.read().lower()
        except OSError:
            continue
        if "closed" in contents:
            return True
        if "open" in contents:
            return False
    return None


def blank_display() -> None:
    if shutil.which("kscreen-doctor"):
        try:
            subprocess.run(
                ["kscreen-doctor", "--dpms", "off"],
                capture_output=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            pass
