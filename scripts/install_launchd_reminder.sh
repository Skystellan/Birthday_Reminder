#!/usr/bin/env bash
set -euo pipefail

LABEL="com.skystellan.shengri-dengta.reminder"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_SUPPORT_DIR="$HOME/Library/Application Support/生辰灯塔"
DB_PATH="$APP_SUPPORT_DIR/birthdays.json"
STATE_PATH="$APP_SUPPORT_DIR/notify_state.json"
PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"
HOUR="${1:-9}"
MINUTE="${2:-0}"
if [ -x "$HOME/.local/bin/uv" ]; then
  UV_BIN="$HOME/.local/bin/uv"
elif [ -x "/opt/homebrew/bin/uv" ]; then
  UV_BIN="/opt/homebrew/bin/uv"
else
  UV_BIN="$(command -v uv || true)"
fi

if [ -z "$UV_BIN" ]; then
  echo "uv not found in current shell PATH." >&2
  exit 1
fi

if ! [[ "$HOUR" =~ ^[0-9]+$ ]] || ! [[ "$MINUTE" =~ ^[0-9]+$ ]]; then
  echo "Hour/minute must be integers." >&2
  exit 1
fi
if [ "$HOUR" -lt 0 ] || [ "$HOUR" -gt 23 ] || [ "$MINUTE" -lt 0 ] || [ "$MINUTE" -gt 59 ]; then
  echo "Hour must be 0-23 and minute must be 0-59." >&2
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$APP_SUPPORT_DIR"

cat >"$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
      <string>/bin/zsh</string>
      <string>-lc</string>
      <string>cd '${PROJECT_DIR}' &amp;&amp; '${UV_BIN}' run python birthday_reminder.py --db '${DB_PATH}' due --notify --notify-once-per-day --notify-state-file '${STATE_PATH}'</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
      <key>Hour</key>
      <integer>${HOUR}</integer>
      <key>Minute</key>
      <integer>${MINUTE}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>${APP_SUPPORT_DIR}/launchd.out.log</string>
    <key>StandardErrorPath</key>
    <string>${APP_SUPPORT_DIR}/launchd.err.log</string>
    <key>RunAtLoad</key>
    <true/>
  </dict>
</plist>
EOF

launchctl unload "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl load "$PLIST_PATH"

echo "Installed launchd reminder: $PLIST_PATH"
echo "Schedule: ${HOUR}:${MINUTE}"
