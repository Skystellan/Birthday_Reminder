#!/usr/bin/env bash
set -euo pipefail

SRC="${1:-$(pwd)/birthdays.json}"
APP_DIR="$HOME/Library/Application Support/生辰灯塔"
DST="$APP_DIR/birthdays.json"

if [ ! -f "$SRC" ]; then
  echo "Source data file not found: $SRC" >&2
  exit 1
fi

mkdir -p "$APP_DIR"

if [ -f "$DST" ]; then
  BACKUP="$APP_DIR/birthdays.backup.$(date +%Y%m%d%H%M%S).json"
  cp "$DST" "$BACKUP"
  echo "Backup created: $BACKUP"
fi

cp "$SRC" "$DST"
echo "Imported to: $DST"
