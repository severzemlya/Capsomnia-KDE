#!/usr/bin/env bash
# Capsomnia for KDE — uninstaller.
# Stops the service (restoring normal sleep), removes installed files, and
# restores any PowerDevil lid override left behind.
set -euo pipefail

SHARE_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/capsomnia"
BIN_DIR="$HOME/.local/bin"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

echo "==> Stopping and disabling service"
systemctl --user disable --now capsomnia.service 2>/dev/null || true

# Belt and suspenders: kill any stray tray process and inhibitor, and make sure
# a leftover PowerDevil override is restored before we delete the code.
pkill -f "python3 -m capsomnia" 2>/dev/null || true
if [ -d "$SHARE_DIR/capsomnia" ]; then
  PYTHONPATH="$SHARE_DIR" python3 - <<'PY' 2>/dev/null || true
from capsomnia.power import PowerController
from capsomnia.config import RecoveryState
PowerController(RecoveryState()).recover_on_startup()
PY
fi

echo "==> Removing files"
rm -f "$UNIT_DIR/capsomnia.service"
rm -f "$BIN_DIR/capsomnia"
rm -f "$APP_DIR/capsomnia.desktop"
rm -f "$ICON_DIR/capsomnia.svg"
rm -rf "$SHARE_DIR"
systemctl --user daemon-reload 2>/dev/null || true

echo "==> Done. Normal sleep behavior restored."
echo "    Preferences remain in ~/.config/capsomnia (delete manually if desired)."
