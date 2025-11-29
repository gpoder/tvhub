#!/usr/bin/env bash
set -e

echo "== TVHub setup =="

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

# Basic packages
apt-get update
apt-get install -y python3 python3-pip python3-venv curl jq android-tools-adb

# Create user
id -u tvhub >/dev/null 2>&1 || useradd -r -s /usr/sbin/nologin tvhub

# Install app to /opt/tvhub
mkdir -p /opt/tvhub
cp -r . /opt/tvhub
cd /opt/tvhub

python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

mkdir -p /var/lib/tvhub
chown -R tvhub:tvhub /opt/tvhub /var/lib/tvhub

# Copy helper script
install -m 755 scripts/gtv-key.sh /usr/local/bin/gtv-key.sh

# Systemd units
cp systemd/tvhub.service /etc/systemd/system/
cp systemd/tvhub-discover.service /etc/systemd/system/
cp systemd/tvhub-discover.timer /etc/systemd/system/

systemctl daemon-reload
systemctl enable tvhub.service tvhub-discover.timer
systemctl start tvhub.service tvhub-discover.timer

echo "== TVHub installed =="
echo "Web UI: http://<this-host>:10001/remote"
