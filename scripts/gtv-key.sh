#!/bin/bash
# Usage: gtv-key.sh <device-id> <keycode-or-name>
# This script expects devices.json to be written by tvhub discovery.
DB="/var/lib/tvhub/devices.json"
ADB_BIN="${TVHUB_ADB_BIN:-/opt/platform-tools/adb}"

DEVICE_ID="$1"
KEY="$2"

if [ -z "$DEVICE_ID" ] || [ -z "$KEY" ]; then
  echo "Usage: $0 <device-id> <key>"
  exit 1
fi

if [ ! -f "$DB" ]; then
  echo "devices.json not found at $DB"
  exit 1
fi

ADDR=$(python3 - <<EOF
import json
p = "$DB"
try:
    data = json.load(open(p))
    dev = data.get("$DEVICE_ID")
    if dev:
        print(dev["address"])
except Exception:
    pass
EOF
)

if [ -z "$ADDR" ]; then
  echo "Device $DEVICE_ID not found in registry"
  exit 1
fi

$ADB_BIN connect "$ADDR" >/dev/null 2>&1

# Map some names here for convenience; numeric codes can pass through.
case "$KEY" in
  HOME) KEY=3 ;;
  BACK) KEY=4 ;;
  UP) KEY=19 ;;
  DOWN) KEY=20 ;;
  LEFT) KEY=21 ;;
  RIGHT) KEY=22 ;;
  SELECT|OK|ENTER) KEY=23 ;;
  PLAY) KEY=126 ;;
  PAUSE) KEY=127 ;;
  STOP) KEY=86 ;;
  NEXT) KEY=87 ;;
  PREVIOUS) KEY=88 ;;
  REWIND) KEY=89 ;;
  FAST_FORWARD) KEY=90 ;;
  MUTE) KEY=164 ;;
  VOLUME_UP) KEY=24 ;;
  VOLUME_DOWN) KEY=25 ;;
esac

$ADB_BIN -s "$ADDR" shell input keyevent "$KEY"
