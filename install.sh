#!/usr/bin/env bash
# Capsomnia for KDE — source installer.
#
# Installs the tray app into ~/.local, registers a systemd user service for
# autostart + crash recovery, and starts it. No root is needed except to
# apt-install python3-pyqt6 if it is missing.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SHARE_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/capsomnia"
BIN_DIR="$HOME/.local/bin"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

echo "==> Checking PyQt6"
if ! python3 -c "import PyQt6" 2>/dev/null; then
  echo "    python3-pyqt6 not found — installing via apt (sudo)"
  sudo apt-get update -qq
  sudo apt-get install -y python3-pyqt6
fi

echo "==> Installing app to $SHARE_DIR"
rm -rf "$SHARE_DIR/capsomnia"
mkdir -p "$SHARE_DIR"
cp -r "$SCRIPT_DIR/capsomnia" "$SHARE_DIR/capsomnia"

echo "==> Installing launcher to $BIN_DIR/capsomnia"
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/capsomnia" <<EOF
#!/usr/bin/env bash
export PYTHONPATH="$SHARE_DIR\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m capsomnia "\$@"
EOF
chmod +x "$BIN_DIR/capsomnia"

echo "==> Installing desktop entry and icon"
mkdir -p "$APP_DIR" "$ICON_DIR"
install -m644 "$SCRIPT_DIR/capsomnia.desktop" "$APP_DIR/capsomnia.desktop"
install -m644 "$SCRIPT_DIR/resources/capsomnia.svg" "$ICON_DIR/capsomnia.svg"

echo "==> Installing systemd user service"
mkdir -p "$UNIT_DIR"
install -m644 "$SCRIPT_DIR/systemd/capsomnia.service" "$UNIT_DIR/capsomnia.service"
systemctl --user daemon-reload
systemctl --user enable --now capsomnia.service

if ! echo ":$PATH:" | grep -q ":$BIN_DIR:"; then
  echo "    NOTE: $BIN_DIR is not on your PATH; add it to run 'capsomnia' directly."
fi

echo "==> Done. Capsomnia is running in the system tray."
echo "    Toggle Caps Lock to arm/disarm the keep-awake switch."
