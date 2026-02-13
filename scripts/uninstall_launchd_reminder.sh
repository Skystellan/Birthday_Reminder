#!/usr/bin/env bash
set -euo pipefail

LABEL="com.skystellan.shengri-dengta.reminder"
PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"

if [ -f "$PLIST_PATH" ]; then
  launchctl unload "$PLIST_PATH" >/dev/null 2>&1 || true
  rm -f "$PLIST_PATH"
  echo "Removed: $PLIST_PATH"
else
  echo "No launchd plist found: $PLIST_PATH"
fi
