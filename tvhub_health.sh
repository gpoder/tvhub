#!/bin/bash
OUT="tvhub_health_$(date +%Y%m%d_%H%M%S).log"

echo "===================================================" >> "$OUT"
echo "TVHub Health Check - $(date)" >> "$OUT"
echo "===================================================" >> "$OUT"
echo "" >> "$OUT"

log_section() {
    echo "" >> "$OUT"
    echo "---------------------------------------------------" >> "$OUT"
    echo "$1" >> "$OUT"
    echo "---------------------------------------------------" >> "$OUT"
}

# ----------------------------------------------------
# 1. Check systemd services
# ----------------------------------------------------
log_section "SYSTEMD SERVICES STATUS"

for svc in tvhub tvhub-discover tvhub-discover.timer; do
    echo "### $svc:" >> "$OUT"
    systemctl status "$svc" --no-pager -l 2>&1 >> "$OUT"
    echo "" >> "$OUT"
done

# ----------------------------------------------------
# 2. Identify tvhub process & python path
# ----------------------------------------------------
log_section "PROCESS & PYTHON PATH CHECK"

PID=$(pidof /opt/tvhub/venv/bin/python)
if [ -z "$PID" ]; then
    PID=$(pidof python)
fi

if [ -z "$PID" ]; then
    echo "❌ No tvhub python process running!" >> "$OUT"
else
    echo "tvhub python PID: $PID" >> "$OUT"
    echo "" >> "$OUT"

    # Show command
    ps -fp "$PID" >> "$OUT"
    echo "" >> "$OUT"

    # Show environment seen by the process
    echo "### Environment for PID $PID" >> "$OUT"
    tr '\0' '\n' < /proc/$PID/environ | sort >> "$OUT"
    echo "" >> "$OUT"

    # Check open files
    echo "### lsof for PID $PID (looking for devices.json)" >> "$OUT"
    lsof -p $PID 2>/dev/null | grep -i devices.json >> "$OUT"
    echo "" >> "$OUT"
fi

# ----------------------------------------------------
# 3. Permissions check
# ----------------------------------------------------
log_section "PERMISSIONS CHECK"

echo "### Directory /var/lib/tvhub:" >> "$OUT"
ls -ld /var/lib/tvhub >> "$OUT"

echo "### File /var/lib/tvhub/devices.json:" >> "$OUT"
ls -l /var/lib/tvhub/devices.json 2>>"$OUT" >> "$OUT"
echo "" >> "$OUT"

echo "### tvhub user permissions test:" >> "$OUT"
sudo -u tvhub test -r /var/lib/tvhub/devices.json \
    && echo "tvhub CAN read devices.json" >> "$OUT" \
    || echo "❌ tvhub CANNOT read devices.json" >> "$OUT"
sudo -u tvhub test -w /var/lib/tvhub/devices.json \
    && echo "tvhub CAN write devices.json" >> "$OUT" \
    || echo "⚠ tvhub cannot write devices.json" >> "$OUT"

# ----------------------------------------------------
# 4. Check Python environment
# ----------------------------------------------------
log_section "PYTHON ENVIRONMENT CHECK"

if [ -f /opt/tvhub/venv/bin/python3 ]; then
    /opt/tvhub/venv/bin/python3 -V 2>&1 >> "$OUT"
    echo "Installed Python packages:" >> "$OUT"
    /opt/tvhub/venv/bin/pip list >> "$OUT"
else
    echo "Python venv not found at /opt/tvhub/venv" >> "$OUT"
fi

# ----------------------------------------------------
# 5. Validate devices.json
# ----------------------------------------------------
log_section "DEVICES.JSON CHECK"

DEV="/var/lib/tvhub/devices.json"

if [ -f "$DEV" ]; then
    echo "devices.json exists." >> "$OUT"
    echo "" >> "$OUT"

    echo "### Syntax check:" >> "$OUT"
    jq . "$DEV" >/dev/null 2>>"$OUT" \
        && echo "JSON valid" >> "$OUT" \
        || echo "❌ INVALID JSON" >> "$OUT"

    echo "" >> "$OUT"
    echo "Contents:" >> "$OUT"
    cat "$DEV" >> "$OUT"

else
    echo "❌ devices.json missing!" >> "$OUT"
fi

# ----------------------------------------------------
# 6. Detect stray devices.json in /opt
# ----------------------------------------------------
log_section "SEARCH FOR STRAY DEVICES.JSON"

find /opt/tvhub -maxdepth 3 -name devices.json 2>/dev/null >> "$OUT"

# ----------------------------------------------------
# 7. Registry Diagnostics (Python one-shot)
# ----------------------------------------------------
log_section "PYTHON REGISTRY SELF-CHECK"

cat << 'EOF' | /opt/tvhub/venv/bin/python3 >> "$OUT" 2>&1
from tvhub.registry import DeviceRegistry
import os
print("Python sees TVHUB_DATA_DIR =", os.environ.get("TVHUB_DATA_DIR"))
r = DeviceRegistry()
print("Registry FILE IS:", r.path)
try:
    print("Registry LOAD RESULT:", r.load())
except Exception as e:
    print("Registry LOAD ERROR:", e)
EOF

# ----------------------------------------------------
# 8. ADB check
# ----------------------------------------------------
log_section "ADB CHECK"

if [ -x /opt/platform-tools/adb ]; then
    echo "adb found at /opt/platform-tools/adb" >> "$OUT"
    /opt/platform-tools/adb version >> "$OUT" 2>&1
else
    echo "❌ adb not found at /opt/platform-tools/adb" >> "$OUT"
fi

# ----------------------------------------------------
# 9. API test
# ----------------------------------------------------
log_section "API TEST"

curl -s http://127.0.0.1:10001/api/devices | jq . >> "$OUT" 2>&1

# ----------------------------------------------------
# 10. Summary
# ----------------------------------------------------
log_section "SUMMARY"
echo "Health check completed." >> "$OUT"
echo "Output saved to: $OUT" >> "$OUT"
echo "" >> "$OUT"

echo ""
echo "✔ Health check complete"
echo "➡ Please upload the file:  $OUT"
