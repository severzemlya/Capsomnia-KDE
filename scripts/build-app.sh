#!/bin/zsh
set -euo pipefail

APP_NAME="Capsomnia"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
APP_BUNDLE="$DIST_DIR/$APP_NAME.app"
CONTENTS_DIR="$APP_BUNDLE/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

cd "$ROOT_DIR"
/usr/bin/swift build -c release >&2

/bin/rm -rf "$APP_BUNDLE"
/bin/mkdir -p "$MACOS_DIR" "$RESOURCES_DIR"

/usr/bin/install -m 0755 ".build/release/$APP_NAME" "$MACOS_DIR/$APP_NAME"
/usr/bin/install -m 0644 "resources/Info.plist" "$CONTENTS_DIR/Info.plist"
/usr/bin/install -m 0644 "resources/AppIcon.icns" "$RESOURCES_DIR/AppIcon.icns"

echo "$APP_BUNDLE"
