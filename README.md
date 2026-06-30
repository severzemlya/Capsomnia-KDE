# Capsomnia

<p align="center">
  <img src="resources/CapsomniaIcon.svg" alt="Capsomnia icon" width="128" height="128">
</p>

[日本語 README](README.ja.md) · [Website](https://fuji-mak.github.io/Capsomnia/) · [Releases](https://github.com/fuji-mak/Capsomnia/releases)

Current version: `0.3.0`

Capsomnia is a small macOS menu bar app that turns Caps Lock into a physical keep-awake switch for closed-lid MacBook work.

Turn Caps Lock on when local work should keep running. Turn Caps Lock off when you want normal sleep behavior back.

## Quick Start

Requirements:

- macOS 14 or later
- Swift 6 toolchain
- Administrator access during installation

Install from source:

```sh
git clone https://github.com/fuji-mak/Capsomnia.git
cd Capsomnia
./scripts/install.sh
```

The installer builds `Capsomnia.app` locally, places it in `~/Applications/`, installs the privileged sleep-control helper, adds a narrow sudoers rule, and starts the LaunchAgent. Capsomnia starts automatically at login after installation.

Capsomnia is currently a developer-oriented source distribution. A signed and notarized app or package is not available yet.

## How It Works

- Caps Lock on: runs `pmset -a disablesleep 1`
- Caps Lock off: runs `pmset -a disablesleep 0`
- Lid closed while Caps Lock is on: optionally runs `pmset displaysleepnow` so the display can sleep while work continues
- Yellow-green menu bar dot: system sleep is disabled
- Gray menu bar dot: normal sleep behavior
- Quitting the app restores normal sleep behavior

Capsomnia is useful for long-running local jobs, AI coding agents, SSH sessions, builds, downloads, and unattended scripts.

## Settings

On first launch, Capsomnia opens a small initial settings window where you can choose:

- whether to show the menu bar dot
- English or Japanese

Open Capsomnia again later to change:

- menu bar dot visibility
- display sleep when the lid closes, enabled by default
- language
- opening at login, enabled by default

You can open Capsomnia from `~/Applications/Capsomnia.app` or from the menu bar item while it is visible.

## Why Not `caffeinate`?

`caffeinate` is useful for preventing idle sleep while your Mac is open. Closing a MacBook lid is different: normal `caffeinate` assertions do not reliably keep local jobs running in closed-lid use.

Capsomnia uses `pmset -a disablesleep 1`, which disables system sleep itself. This is more suitable when you explicitly want local work to continue while the lid is closed.

## Safety Notes

- Closed-lid background work is the intended use case.
- Sleep-disabled closed-lid use can increase heat and battery drain.
- Use good judgment for airflow, power, and runtime when leaving your Mac unattended.
- Capsomnia is a manual switch: Caps Lock on means "keep running"; Caps Lock off means "normal sleep behavior".

## Update

From an existing clone:

```sh
cd Capsomnia
git pull
./scripts/install.sh
```

The install script overwrites the app bundle, helper, sudoers rule, and LaunchAgent with the current version.

## Uninstall

```sh
./scripts/uninstall.sh
```

The uninstaller unloads the LaunchAgent, removes `~/Applications/Capsomnia.app`, removes the helper, removes the sudoers rule, and restores normal sleep behavior.

## Security Model

Capsomnia's menu bar app does not run as root. System sleep settings require elevated privileges, so Capsomnia uses a small fixed helper through passwordless `sudo`.

The app can only invoke:

```sh
sudo -n /Library/PrivilegedHelperTools/capsomnia-pmset on
sudo -n /Library/PrivilegedHelperTools/capsomnia-pmset off
sudo -n /Library/PrivilegedHelperTools/capsomnia-pmset display-sleep
```

The sudoers rule is limited to those three exact commands. The helper only accepts `on`, `off`, and `display-sleep`, and only calls:

```sh
/usr/bin/pmset -a disablesleep 1
/usr/bin/pmset -a disablesleep 0
/usr/bin/pmset displaysleepnow
```

## Logs and Troubleshooting

Logs are written to:

```text
~/Library/Logs/Capsomnia/
```

Check whether sleep is disabled:

```sh
pmset -g | grep disablesleep
```

Restart the LaunchAgent:

```sh
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.github.fuji-mak.capsomnia.plist"
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.github.fuji-mak.capsomnia.plist"
```

Check the helper permissions:

```sh
sudo -n -l /Library/PrivilegedHelperTools/capsomnia-pmset on \
  /Library/PrivilegedHelperTools/capsomnia-pmset off \
  /Library/PrivilegedHelperTools/capsomnia-pmset display-sleep
```

If the helper permission check fails, run `./scripts/install.sh` again. If the menu bar dot does not react immediately, Capsomnia also polls the Caps Lock state once per second as a fallback.

## Website Development

The GitHub Pages site lives in `docs/`. The HTML is written with Tailwind CSS utility classes.

```sh
npm install
npm run build:site
```

Main files:

- `docs/index.html`: page structure and Tailwind classes
- `docs/styles.input.css`: site variables, small custom CSS, and Tailwind input
- `docs/styles.css`: generated CSS
- `docs/capsomnia.js`: language switcher and copy behavior

## Project Status

Capsomnia is in early public release. See [CHANGELOG.md](CHANGELOG.md) for release history and [SECURITY.md](SECURITY.md) for vulnerability reporting.

## License

MIT
