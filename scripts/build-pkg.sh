#!/bin/zsh
set -euo pipefail

APP_NAME="Capsomnia"
LABEL="com.github.fuji-mak.capsomnia"
TEAM_ID="ZJZ8627852"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(/usr/bin/plutil -extract CFBundleShortVersionString raw -o - "$ROOT_DIR/resources/Info.plist")"
BUNDLE_ID="$(/usr/bin/plutil -extract CFBundleIdentifier raw -o - "$ROOT_DIR/resources/Info.plist")"
APP_SIGN_IDENTITY="${CAPSOMNIA_APP_SIGN_IDENTITY:-Developer ID Application: Taketo Fujimaki ($TEAM_ID)}"
PKG_SIGN_IDENTITY="${CAPSOMNIA_PKG_SIGN_IDENTITY:-Developer ID Installer: Taketo Fujimaki ($TEAM_ID)}"
OUT_DIR="${1:-$ROOT_DIR/dist}"
SIGNED_PKG="$OUT_DIR/$APP_NAME-$VERSION.pkg"
UNSIGNED_PKG="$OUT_DIR/$APP_NAME-$VERSION-unsigned.pkg"

work_dir=""
cleanup() {
  [[ -n "$work_dir" ]] && /bin/rm -rf "$work_dir"
}
trap cleanup EXIT

mkdir -p "$OUT_DIR"
work_dir="$(/usr/bin/mktemp -d)"
payload_root="$work_dir/payload"
scripts_dir="$work_dir/scripts"
built_app="$work_dir/$APP_NAME.app"

echo "Building $APP_NAME.app..."
"$ROOT_DIR/scripts/build-app.sh" "$built_app" >/dev/null

echo "Signing $APP_NAME.app with: $APP_SIGN_IDENTITY"
/usr/bin/codesign --force --deep --timestamp --options runtime \
  --sign "$APP_SIGN_IDENTITY" \
  "$built_app"
/usr/bin/codesign --verify --deep --strict --verbose=2 "$built_app"

echo "Preparing package payload..."
/bin/mkdir -p \
  "$payload_root/Applications" \
  "$payload_root/Library/PrivilegedHelperTools" \
  "$payload_root/Library/LaunchAgents" \
  "$scripts_dir"

COPYFILE_DISABLE=1 /usr/bin/ditto "$built_app" "$payload_root/Applications/$APP_NAME.app"
/usr/bin/install -m 0755 "$ROOT_DIR/support/capsomnia-pmset" \
  "$payload_root/Library/PrivilegedHelperTools/capsomnia-pmset"

cat > "$payload_root/Library/LaunchAgents/$LABEL.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>

  <key>ProgramArguments</key>
  <array>
    <string>/Applications/$APP_NAME.app/Contents/MacOS/$APP_NAME</string>
  </array>

  <key>RunAtLoad</key>
  <true/>
</dict>
</plist>
PLIST

COPYFILE_DISABLE=1 /usr/bin/xattr -cr "$payload_root" 2>/dev/null || true
/usr/bin/find "$payload_root" -name '._*' -type f -delete
/usr/bin/codesign --verify --deep --strict --verbose=2 "$payload_root/Applications/$APP_NAME.app"

cat > "$scripts_dir/postinstall" <<'POSTINSTALL'
#!/bin/zsh
set -euo pipefail

APP_NAME="Capsomnia"
LABEL="com.github.fuji-mak.capsomnia"
HELPER_PATH="/Library/PrivilegedHelperTools/capsomnia-pmset"
LEGACY_HELPER_PATH="/usr/local/sbin/capsomnia-pmset"
SUDOERS_PATH="/etc/sudoers.d/capsomnia"
SYSTEM_LAUNCH_AGENT="/Library/LaunchAgents/$LABEL.plist"

console_user="$(/usr/bin/stat -f "%Su" /dev/console 2>/dev/null || true)"
if [[ -z "$console_user" || "$console_user" == "root" || "$console_user" == "_mbsetupuser" ]]; then
  console_user="${SUDO_USER:-}"
fi

if [[ -z "$console_user" || "$console_user" == "root" || "$console_user" == *[!A-Za-z0-9._-]* ]]; then
  echo "Capsomnia installer could not determine the target user for sudoers." >&2
  exit 1
fi

console_uid="$(/usr/bin/id -u "$console_user")"
console_home="$(/usr/bin/dscl . -read "/Users/$console_user" NFSHomeDirectory 2>/dev/null | /usr/bin/awk '{print $2}')"

/bin/mkdir -p "$(dirname "$HELPER_PATH")" "$(dirname "$SUDOERS_PATH")"
/usr/sbin/chown root:wheel "$(dirname "$HELPER_PATH")" "$(dirname "$SUDOERS_PATH")"
/bin/chmod 0755 "$(dirname "$HELPER_PATH")" "$(dirname "$SUDOERS_PATH")"
/usr/sbin/chown root:wheel "$HELPER_PATH" "$SYSTEM_LAUNCH_AGENT"
/bin/chmod 0755 "$HELPER_PATH"
/bin/chmod 0644 "$SYSTEM_LAUNCH_AGENT"
/bin/rm -f "$LEGACY_HELPER_PATH"
/usr/bin/find \
  "/Applications/$APP_NAME.app" \
  "/Library/PrivilegedHelperTools" \
  "/Library/LaunchAgents" \
  -name '._*' -type f -delete 2>/dev/null || true

sudoers_tmp="$(/usr/bin/mktemp)"
cleanup() {
  /bin/rm -f "$sudoers_tmp"
}
trap cleanup EXIT

cat > "$sudoers_tmp" <<EOF
# Allow Capsomnia to toggle only its fixed pmset helper.
$console_user ALL=(root) NOPASSWD: $HELPER_PATH on, $HELPER_PATH off, $HELPER_PATH display-sleep
EOF

/usr/sbin/visudo -cf "$sudoers_tmp"
/usr/bin/install -o root -g wheel -m 0440 "$sudoers_tmp" "$SUDOERS_PATH"

if [[ -n "$console_home" ]]; then
  legacy_user_agent="$console_home/Library/LaunchAgents/$LABEL.plist"
  /bin/launchctl bootout "gui/$console_uid" "$legacy_user_agent" 2>/dev/null || true
  /bin/rm -f "$legacy_user_agent"
fi

/bin/launchctl bootout "gui/$console_uid" "$SYSTEM_LAUNCH_AGENT" 2>/dev/null || true
/bin/launchctl bootstrap "gui/$console_uid" "$SYSTEM_LAUNCH_AGENT" 2>/dev/null || true
/bin/launchctl enable "gui/$console_uid/$LABEL" 2>/dev/null || true

exit 0
POSTINSTALL
/bin/chmod 0755 "$scripts_dir/postinstall"

echo "Building unsigned package..."
/bin/rm -f "$UNSIGNED_PKG" "$SIGNED_PKG"
COPYFILE_DISABLE=1 /usr/bin/pkgbuild \
  --root "$payload_root" \
  --scripts "$scripts_dir" \
  --identifier "$BUNDLE_ID.pkg" \
  --version "$VERSION" \
  --install-location "/" \
  --ownership recommended \
  --min-os-version 14.0 \
  "$UNSIGNED_PKG"

echo "Signing package with: $PKG_SIGN_IDENTITY"
COPYFILE_DISABLE=1 /usr/bin/productsign \
  --sign "$PKG_SIGN_IDENTITY" \
  --timestamp \
  "$UNSIGNED_PKG" \
  "$SIGNED_PKG"

/usr/sbin/pkgutil --check-signature "$SIGNED_PKG"

echo "$SIGNED_PKG"
