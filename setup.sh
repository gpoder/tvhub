#!/usr/bin/env bash
set -e

echo "==============================================="
echo "   TVHub Installer – Updated Full Version"
echo "==============================================="

INSTALL_DIR="/opt/tvhub"
DATA_DIR="/var/lib/tvhub"
ADB_DIR="/opt/platform-tools"
VENV="$INSTALL_DIR/venv"

echo ">>> Updating apt packages..."
apt update
apt install -y python3 python3-venv python3-pip python3-dev curl unzip jq nmap git

echo ">>> Creating tvhub user..."
if ! id -u tvhub >/dev/null 2>&1; then
    useradd -r -s /usr/sbin/nologin -d /opt/tvhub tvhub
fi

echo ">>> Creating directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$DATA_DIR"
chown -R tvhub:tvhub "$DATA_DIR"

echo ">>> Removing old env if exists..."
rm -rf "$VENV"

echo ">>> Creating Python virtual environment..."
python3 -m venv "$VENV"
source "$VENV/bin/activate"

echo ">>> Installing Python dependencies inside venv..."
pip install --upgrade pip
pip install flask zeroconf requests lxml

deactivate

echo ">>> Installing Android platform-tools..."
rm -rf "$ADB_DIR"
mkdir -p "$ADB_DIR"
curl -L https://dl.google.com/android/repository/platform-tools-latest-linux.zip -o /tmp/platform-tools.zip
unzip -o /tmp/platform-tools.zip -d /tmp/
mv /tmp/platform-tools/* "$ADB_DIR/"
chmod +x "$ADB_DIR/adb"

echo ">>> Fixing PATH for all users..."
cat >/etc/profile.d/tvhub_adb.sh <<EOF
export PATH=\$PATH:/opt/platform-tools
EOF

chmod +x /etc/profile.d/tvhub_adb.sh

echo ">>> Installing TVHub source files..."
# Assumes you're running inside the project folder
cp -r tvhub "$INSTALL_DIR/"
chown -R tvhub:tvhub "$INSTALL_DIR"

echo ">>> Writing systemd service: tvhub.service"
cat >/etc/systemd/system/tvhub.service <<EOF
[Unit]
Description=TVHub Flask API
After=network.target

[Service]
Type=simple
User=tvhub
Group=tvhub
WorkingDirectory=/opt/tvhub
Environment=TVHUB_DATA_DIR=$DATA_DIR
Environment=TVHUB_ADB_BIN=/opt/platform-tools/adb
ExecStart=/opt/tvhub/venv/bin/python -m tvhub.app
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

echo ">>> Writing systemd service: tvhub-discover.service"
cat >/etc/systemd/system/tvhub-discover.service <<EOF
[Unit]
Description=TVHub discovery run

[Service]
Type=oneshot
User=tvhub
Group=tvhub
WorkingDirectory=/opt/tvhub
Environment=TVHUB_DATA_DIR=$DATA_DIR
ExecStart=/opt/tvhub/venv/bin/python -m tvhub.discover_all
EOF

echo ">>> Writing systemd timer: tvhub-discover.timer"
cat >/etc/systemd/system/tvhub-discover.timer <<EOF
[Unit]
Description=Run TVHub discovery every 30 seconds

[Timer]
OnBootSec=15
OnUnitActiveSec=30
Unit=tvhub-discover.service

[Install]
WantedBy=timers.target
EOF

echo ">>> Reloading systemd..."
systemctl daemon-reload

echo ">>> Enabling and starting services..."
systemctl enable tvhub.service
systemctl enable tvhub-discover.timer

systemctl restart tvhub.service
systemctl restart tvhub-discover.timer

echo ""
echo "==============================================="
echo "        TVHub Installation Complete!"
echo "-----------------------------------------------"
echo " API running at:        http://<server>:10001"
echo " Discovery runs every:  30 seconds"
echo " ADB installed at:      /opt/platform-tools/adb"
echo " Service user:          tvhub"
echo "==============================================="
