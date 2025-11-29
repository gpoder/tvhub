import os
from pathlib import Path

# Base directory for data (can be overridden by env TVHUB_DATA_DIR)
DATA_DIR = Path(os.environ.get("TVHUB_DATA_DIR", "/var/lib/tvhub"))

# File for device registry
DEVICES_FILE = DATA_DIR / "devices.json"

# Path to adb binary (can be overridden)
ADB_BIN = os.environ.get("TVHUB_ADB_BIN", "/opt/platform-tools/adb")

# Hisense defaults
HISENSE_DMR_PORT = 2870
HISENSE_INSTANCE_ID = 0
HISENSE_CHANNEL = "Master"
