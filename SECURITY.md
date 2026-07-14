# Security

## Model

Capsomnia for KDE runs entirely as your normal user — **no root privileges** and
no setuid/privileged helper. It uses only unprivileged, standard interfaces:

- **Reading Caps Lock:** the kernel LED state at
  `/sys/class/leds/*capslock*/brightness`. No key events are read and no input
  device is opened, so there is no keylogging surface and no elevated permission.
- **Blocking idle sleep:** an unprivileged `systemd-inhibit` block inhibitor.
- **Suppressing lid-close suspend:** KDE PowerDevil's own `LidAction` setting in
  your user config (`~/.config/powerdevilrc`), reloaded via PowerDevil's D-Bus
  `refreshStatus`. The original values are saved and restored on disengage, and
  recovered on next launch if the app is killed while armed.

Capsomnia makes no network requests, collects no telemetry, and requires no
account.

## Reporting a vulnerability

Please open a private security advisory on the GitHub repository, or contact the
maintainer directly. Do not file public issues for security reports.
