# Capsomnia for KDE

A **KDE Plasma** port of [Capsomnia](https://github.com/fuji-mak/Capsomnia), the
tiny macOS app that turns **Caps Lock into a physical keep-awake switch** for
closed-lid laptop work.

Turn Caps Lock **on** when local work should keep running with the lid closed —
AI coding agents, SSH sessions, builds, downloads, unattended scripts. Turn Caps
Lock **off** to restore normal sleep behavior. The Caps Lock LED physically shows
the current state, exactly like the macOS original.

Capsomnia makes no network requests, collects no telemetry, and needs no account.

## Requirements

- KDE Plasma 6 (Wayland or X11) with PowerDevil — the default KDE power manager
- Python 3.10+ and `python3-pyqt6` (the installer offers to `apt install` it)
- systemd user session (standard on KDE distributions)

Tested on TUXEDO OS 24.04 (Ubuntu 24.04 base), Plasma 6.5, Wayland.

## Install

```sh
git clone https://github.com/severzemlya/Capsomnia.git
cd Capsomnia
./install.sh
```

The installer copies the app into `~/.local`, installs a systemd **user** service
for autostart and crash recovery, and starts it. A green LED dot appears in the
system tray. **No root privileges are used** beyond an optional `apt install
python3-pyqt6`.

## How it works

While Caps Lock is on, Capsomnia engages two mechanisms together and reverses
them when Caps Lock goes off:

1. **A systemd-logind block inhibitor** (`sleep:idle:handle-lid-switch`), taken
   unprivileged via `systemd-inhibit`. This blocks idle and automatic system
   sleep.
2. **A temporary PowerDevil lid-action override.** On a KDE laptop, PowerDevil —
   not logind — owns the lid switch, so a plain inhibitor does **not** reliably
   stop lid-close suspend (the same reason `caffeinate` is not enough on macOS).
   Capsomnia sets PowerDevil's `LidAction` to *do nothing* for every power
   profile (AC / Battery / LowBattery) while armed, saving the originals and
   restoring them the moment Caps Lock turns off.

This is why the whole macOS sudo-helper / sudoers / code-signing machinery is
**unnecessary here** — everything runs as your normal user.

The Caps Lock LED state is read from the kernel at
`/sys/class/leds/*capslock*/brightness` every 250 ms. **No key events are read
and no Input Monitoring permission exists or is needed.**

### Tray states

| Dot | Meaning |
| --- | --- |
| 🟢 lime green (glowing) | Caps Lock on — sleep suppressed |
| ⚪ grey | Caps Lock off — normal sleep |
| 🔴 red | Could not apply / drifted — retrying every 5 s |

Right-click the tray icon for: *Turn display off when lid closes*, *Launch at
login*, *Language* (English / 日本語), *About*, and *Quit*.

## Settings

- **Turn display off when lid closes** — while armed, blanks the panel via
  `kscreen-doctor --dpms off` on lid close while work keeps running (off by
  default). The macOS "display sleep on lid close" equivalent.
- **Launch at login** — enables/disables the systemd user service.
- **Language** — English or Japanese.

Preferences live in `~/.config/capsomnia/config.ini`.

## Safety and recovery

- Capsomnia verifies the suppression is actually in effect after every change and
  every 10 s. On drift or failure the dot turns red and it retries.
- On **normal quit or stop**, normal sleep behavior is always restored.
- On a **hard crash**, the systemd inhibitor is released automatically (the child
  is killed with the parent via `PR_SET_PDEATHSIG`), and the PowerDevil override
  is restored on the next launch from a saved recovery file
  (`~/.config/capsomnia/state.ini`).
- Sleep-disabled closed-lid use can increase heat and battery drain. Use good
  judgment for airflow, power, and runtime when leaving the laptop unattended.

### Manual recovery

If Capsomnia is force-killed and something is left armed:

```sh
# Release any leftover inhibitor
pkill -f "python3 -m capsomnia"
systemd-inhibit --list | grep Capsomnia   # should be empty

# Restore the PowerDevil lid override (reads the saved recovery file)
PYTHONPATH=~/.local/share/capsomnia python3 -c \
  'from capsomnia.power import PowerController; from capsomnia.config import RecoveryState; PowerController(RecoveryState()).recover_on_startup()'
```

Check the lid action directly:

```sh
kreadconfig6 --file powerdevilrc --group Battery --group SuspendAndShutdown --key LidAction
```

## Troubleshooting

- **No tray icon after login:** `systemctl --user status capsomnia` — check it is
  active. `journalctl --user -u capsomnia -e` for logs.
- **Not on KDE?** The inhibitor still blocks idle sleep, but the PowerDevil lid
  override is skipped, so lid-close suspend may not be prevented on other desktops.
- **Caps Lock has no effect:** confirm `cat /sys/class/leds/*capslock*/brightness`
  changes when you toggle Caps Lock.

## Update

```sh
cd Capsomnia && git pull && ./install.sh
```

## Uninstall

```sh
cd Capsomnia
./uninstall.sh
```

Stops the service (restoring normal sleep), restores any PowerDevil override, and
removes installed files. Preferences under `~/.config/capsomnia` are left in place.

## License

MIT, same as upstream.
