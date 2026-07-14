"""Read the physical Caps Lock state from the kernel LED sysfs.

No Input Monitoring / keylogging: we only read the Caps Lock LED brightness
exposed by the kernel at /sys/class/leds/*capslock*/brightness. This reflects
the logical Caps Lock lock state even on keyboards without a physical LED, and
needs no elevated privileges. Mirrors the macOS app, which polls the LED state
rather than reading key events.
"""

from __future__ import annotations

import glob

_LED_GLOB = "/sys/class/leds/*capslock*/brightness"


def led_paths() -> list[str]:
    return sorted(glob.glob(_LED_GLOB))


def read_capslock() -> bool | None:
    """Return True if Caps Lock is on, False if off, None if unreadable.

    If several Caps Lock LEDs exist (multiple keyboards), the state is the OR of
    all readable ones. Returns None only when no LED could be read at all.
    """
    paths = led_paths()
    if not paths:
        return None

    any_read = False
    state = False
    for path in paths:
        try:
            with open(path, "r", encoding="ascii") as fh:
                value = fh.read().strip()
        except OSError:
            continue
        any_read = True
        if value.isdigit() and int(value) > 0:
            state = True

    return state if any_read else None
