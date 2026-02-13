#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

APP_NAME="生辰灯塔"
BUNDLE_ID="com.skystellan.shengri-dengta"
ICON_PATH="assets/生辰灯塔.icns"
PLIST_BUDDY="/usr/libexec/PlistBuddy"

rm -rf build dist "${APP_NAME}.spec"

uv run --with pillow python scripts/generate_icon.py --output-icns "$ICON_PATH"

uv run --with pyinstaller pyinstaller \
  --noconfirm \
  --windowed \
  --name "${APP_NAME}" \
  --icon "$ICON_PATH" \
  --osx-bundle-identifier "$BUNDLE_ID" \
  --hidden-import webview.platforms.cocoa \
  --collect-data webview \
  --add-data "templates:templates" \
  --add-data "static:static" \
  desktop_app.py

PLIST="dist/${APP_NAME}.app/Contents/Info.plist"
"$PLIST_BUDDY" -c "Set :CFBundleDisplayName ${APP_NAME}" "$PLIST" || \
  "$PLIST_BUDDY" -c "Add :CFBundleDisplayName string ${APP_NAME}" "$PLIST"
"$PLIST_BUDDY" -c "Set :CFBundleName ${APP_NAME}" "$PLIST" || \
  "$PLIST_BUDDY" -c "Add :CFBundleName string ${APP_NAME}" "$PLIST"
"$PLIST_BUDDY" -c "Set :CFBundleIdentifier ${BUNDLE_ID}" "$PLIST" || \
  "$PLIST_BUDDY" -c "Add :CFBundleIdentifier string ${BUNDLE_ID}" "$PLIST"
"$PLIST_BUDDY" -c "Set :LSApplicationCategoryType public.app-category.productivity" "$PLIST" || \
  "$PLIST_BUDDY" -c "Add :LSApplicationCategoryType string public.app-category.productivity" "$PLIST"
"$PLIST_BUDDY" -c "Set :CFBundleShortVersionString 0.1.0" "$PLIST" || \
  "$PLIST_BUDDY" -c "Add :CFBundleShortVersionString string 0.1.0" "$PLIST"
"$PLIST_BUDDY" -c "Set :CFBundleVersion 1" "$PLIST" || \
  "$PLIST_BUDDY" -c "Add :CFBundleVersion string 1" "$PLIST"

echo "Build complete:"
echo "dist/${APP_NAME}.app"
