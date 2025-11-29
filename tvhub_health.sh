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
# 1. Check system services
# ----------------------------------------------------
log_section "SYSTEMD SERVICES STATUS"

for svc in tvhub tvhub-discover tvhub-discover.timer; do
    echo "### $svc:" >> "$OUT"
    systemctl status "$svc" --no-pager -l 2>&1 >> "$OUT"
    echo "" >> "$OUT"
done

# ----------------------------------------------------
# 2. Extract last logs
# ----------------------------------------------------
log_section "RECENT LOGS (journalctl)"

for svc in tvhub tvhub-discover; do
    echo "### Logs for $svc (last 50 lines)" >> "$OUT"
    journalctl -u "$svc" -n 50 --no-pager >> "$OUT"
    echo "" >> "$OUT"
done

# ----------------------------------------------------
# 3. Check Python venv and module load
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
# 4. Validate devices.json
# ----------------------------------------------------
log_section "DEVICES.JSON CHECK"

DEV="/var/lib/tvhub/devices.json"

if [ -f "$DEV" ]; then
    echo "devices.json exists." >> "$OUT"
    echo "Syntax validation:" >> "$OUT"
    cat "$DEV" | jq . >/dev/null 2>>"$OUT"

    if [ $? -eq 0 ]; then
        echo "JSON is valid." >> "$OUT"
    else
        echo "❌ INVALID JSON (see above)" >> "$OUT"
    fi

    echo "" >> "$OUT"
    echo "Contents:" >> "$OUT"
    cat "$DEV" >> "$OUT"
else
    echo "❌ devices.json missing!" >> "$OUT"
fi

# ----------------------------------------------------
# 5. Check adb path & version
# ----------------------------------------------------
log_section "ADB CHECK"

if [ -x /opt/platform-tools/adb ]; then
    echo "adb found at /opt/platform-tools/adb" >> "$OUT"
    /opt/platform-tools/adb version >> "$OUT" 2>&1
else
    echo "❌ adb not found at /opt/platform-tools/adb" >> "$OUT"
fi

# ----------------------------------------------------
# 6. Scan ports for common TV types
# ----------------------------------------------------
log_section "NETWORK PORT SCAN"

TV_IPS=$(jq -r '.[].address' "$DEV" 2>/dev/null | sed 's/:.*//')

for ip in $TV_IPS; do
    echo "### Checking $ip" >> "$OUT"
    nc -zv "$ip" 1969 2>&1 | sed 's/^/    /' >> "$OUT"
    nc -zv "$ip" 2870 2>&1 | sed 's/^/    /' >> "$OUT"
    echo "" >> "$OUT"
done

# ----------------------------------------------------
# 7. Test API responsiveness
# ----------------------------------------------------
log_section "API TEST"

curl -s http://127.0.0.1:10001/api/devices | jq . >> "$OUT" 2>&1

# ----------------------------------------------------
# 8. Summary
# ----------------------------------------------------
log_section "SUMMARY"

echo "Health check completed." >> "$OUT"
echo "Output saved to: $OUT" >> "$OUT"
echo "" >> "$OUT"

echo ""
echo "✔ Health check complete"
echo "➡ Please upload the file:  $OUT"
