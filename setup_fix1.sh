sudo mkdir -p /opt/tvhub
sudo mkdir -p /var/lib/tvhub
sudo mkdir -p /opt/platform-tools

# 1. Install system dependencies
sudo apt update
sudo apt install -y python3-venv python3-pip python3-dev \
    unzip curl jq nmap git

# 2. Create Python venv
python3 -m venv /opt/tvhub/venv

# 3. Activate venv and install required packages
/opt/tvhub/venv/bin/pip install --upgrade pip
/opt/tvhub/venv/bin/pip install flask zeroconf requests lxml

# 4. Install adb properly
cd /opt/platform-tools
sudo curl -O https://dl.google.com/android/repository/platform-tools-latest-linux.zip
sudo unzip -o platform-tools-latest-linux.zip
sudo mv platform-tools/* .
sudo rm -r platform-tools platform-tools-latest-linux.zip

# 5. Add adb to PATH for all users
echo 'export PATH=$PATH:/opt/platform-tools' | sudo tee /etc/profile.d/tvhub_adb.sh
source /etc/profile.d/tvhub_adb.sh

# 6. Create empty devices DB
echo '{}' | sudo tee /var/lib/tvhub/devices.json

# 7. Fix permissions
sudo chown -R $USER:$USER /opt/tvhub
sudo chown -R $USER:$USER /var/lib/tvhub
sudo chmod 664 /var/lib/tvhub/devices.json

# 8. Restart services
sudo systemctl daemon-reload
sudo systemctl restart tvhub-discover.timer
sudo systemctl restart tvhub-discover.service
sudo systemctl restart tvhub.service
