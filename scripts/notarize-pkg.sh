#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(/usr/bin/plutil -extract CFBundleShortVersionString raw -o - "$ROOT_DIR/resources/Info.plist")"
PKG_PATH="${1:-$ROOT_DIR/dist/Capsomnia-$VERSION.pkg}"
NOTARY_PROFILE="${CAPSOMNIA_NOTARY_PROFILE:-capsomnia-notary}"

if [[ ! -f "$PKG_PATH" ]]; then
  echo "Package not found: $PKG_PATH" >&2
  exit 66
fi

echo "Submitting $PKG_PATH to Apple notary service with profile: $NOTARY_PROFILE"
/usr/bin/xcrun notarytool submit "$PKG_PATH" \
  --keychain-profile "$NOTARY_PROFILE" \
  --wait

echo "Stapling notarization ticket..."
/usr/bin/xcrun stapler staple "$PKG_PATH"

echo "Assessing stapled package..."
/usr/sbin/spctl --assess --type install --verbose "$PKG_PATH"

echo "$PKG_PATH"
