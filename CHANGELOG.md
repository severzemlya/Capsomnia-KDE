# Changelog

## 1.0.0 — KDE Plasma

First release of the Linux / KDE Plasma edition, reworked from the macOS
Capsomnia ([fuji-mak/Capsomnia](https://github.com/fuji-mak/Capsomnia)).

- Caps Lock as a physical keep-awake switch, read from the kernel LED sysfs
  (`/sys/class/leds/*capslock*/brightness`) — no key events, no root.
- Idle sleep blocked with an unprivileged `systemd-inhibit` inhibitor.
- Lid-close suspend suppressed by overriding KDE PowerDevil's `LidAction` for all
  power profiles while armed, reloaded via PowerDevil's D-Bus `refreshStatus` and
  restored on disengage (with crash recovery).
- PyQt6 system-tray UI (green / grey / red LED dot), English / Japanese.
- systemd user service for autostart and crash recovery; install / uninstall
  scripts.
