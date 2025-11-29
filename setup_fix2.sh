#!/usr/bin/env bash
set -euo pipefail

echo "=== TVHub repair/normalise script ==="

TVHUB_DIR="/opt/tvhub"
VENV_DIR="${TVHUB_DIR}/venv"
ADB_DIR="/opt/platform-tools"
ADB_ZIP="/opt/platform-tools-latest-linux.zip"
TVHUB_USER="tvhub"
TVHUB_GROUP="tvhub"
DATA_DIR="/var/lib/tvhub"

echo "[1] Ensure base dirs exist..."
sudo mkdir -p "$TVHUB_DIR" "$ADB_DIR" "$DATA_DIR"
sudo chown -R "$TVHUB_USER:$TVHUB_GROUP" "$TVHUB_DIR" "$DATA_DIR" || true

echo "[2] Ensure Python venv..."
if [ ! -d "$VENV_DIR" ]; then
    sudo python3 -m venv "$VENV_DIR"
    sudo chown -R "$TVHUB_USER:$TVHUB_GROUP" "$VENV_DIR"
fi

echo "[3] Install/upgrade Python deps into venv..."
sudo "$VENV_DIR/bin/pip" install --upgrade pip
sudo "$VENV_DIR/bin/pip" install flask zeroconf requests lxml

echo "[4] Reinstall adb platform-tools cleanly..."
cd /opt
# Clean out existing dir contents but keep directory
sudo rm -rf "$ADB_DIR"/*
# Download fresh zip
sudo curl -L -o "$ADB_ZIP" "https://dl.google.com/android/repository/platform-tools-latest-linux.zip"
# Unzip into /opt/tmp then move
sudo rm -rf /opt/platform-tools.tmp
sudo mkdir -p /opt/platform-tools.tmp
sudo unzip -q "$ADB_ZIP" -d /opt/platform-tools.tmp
sudo mv /opt/platform-tools.tmp/platform-tools/* "$ADB_DIR"/
sudo rmdir /opt/platform-tools.tmp/platform-tools || true
sudo rmdir /opt/platform-tools.tmp || true
sudo chmod +x "$ADB_DIR/adb"
# Optional global symlink
if [ ! -e /usr/local/bin/adb ]; then
    sudo ln -s "$ADB_DIR/adb" /usr/local/bin/adb || true
fi
sudo chown -R "$TVHUB_USER:$TVHUB_GROUP" "$ADB_DIR"

echo "[5] Rewrite systemd units to use venv + adb..."

# tvhub.service
sudo tee /etc/systemd/system/tvhub.service >/dev/null <<EOF
[Unit]
Description=TVHub Flask API
After=network.target

[Service]
Type=simple
User=${TVHUB_USER}
Group=${TVHUB_GROUP}
Environment=TVHUB_DATA_DIR=${DATA_DIR}
Environment=TVHUB_ADB_BIN=${ADB_DIR}/adb
Environment=PATH=${VENV_DIR}/bin:${ADB_DIR}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
WorkingDirectory=${TVHUB_DIR}
ExecStart=${VENV_DIR}/bin/python -m tvhub.app
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# tvhub-discover.service
sudo tee /etc/systemd/system/tvhub-discover.service >/dev/null <<EOF
[Unit]
Description=TVHub discovery run

[Service]
Type=oneshot
User=${TVHUB_USER}
Group=${TVHUB_GROUP}
Environment=TVHUB_DATA_DIR=${DATA_DIR}
Environment=TVHUB_ADB_BIN=${ADB_DIR}/adb
Environment=PATH=${VENV_DIR}/bin:${ADB_DIR}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
WorkingDirectory=${TVHUB_DIR}
ExecStart=${VENV_DIR}/bin/python -m tvhub.discover_all
EOF

# tvhub-discover.timer (unchanged, but re-write for safety)
sudo tee /etc/systemd/system/tvhub-discover.timer >/dev/null <<EOF
[Unit]
Description=Run TVHub discovery every 30 seconds

[Timer]
OnBootSec=15
OnUnitActiveSec=30
Unit=tvhub-discover.service

[Install]
WantedBy=timers.target
EOF

echo "[6] Reload systemd & restart services..."
sudo systemctl daemon-reload
sudo systemctl enable tvhub.service tvhub-discover.timer
sudo systemctl restart tvhub-discover.timer
sudo systemctl restart tvhub.service || true

echo "=== Done. Run health check again when this finishes. ==="
