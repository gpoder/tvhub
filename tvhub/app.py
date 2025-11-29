#!/usr/bin/env python3
from __future__ import annotations
from flask import Flask, jsonify, request, render_template_string
from typing import Dict, Any

from .registry import DeviceRegistry
from .plugins import load_plugins

app = Flask(__name__)

registry = DeviceRegistry()
plugins = load_plugins()

def refresh_registry():
    """Reload devices from devices.json so API sees latest discoveries."""
    try:
        registry.load()
    except Exception as e:
        app.logger.exception("Error refreshing registry: %s", e)

REMOTE_HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>TVHub Remote</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {
      background: #111;
      color: #eee;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 0;
      min-height: 100vh;
      display: flex;
      justify-content: center;
      align-items: center;
    }
    .app {
      background: #222;
      border-radius: 24px;
      padding: 16px;
      box-shadow: 0 0 25px rgba(0,0,0,0.6);
      width: 360px;
      max-width: 100vw;
    }
    h1 {
      font-size: 1.3rem;
      margin: 0 0 4px 0;
      text-align: center;
    }
    .subtitle {
      font-size: 0.75rem;
      text-align: center;
      color: #aaa;
      margin-bottom: 12px;
    }
    select, input[type=range] {
      width: 100%;
    }
    .section {
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px solid #333;
    }
    .label {
      font-size: 0.8rem;
      margin-bottom: 4px;
      color: #ccc;
    }
    .status {
      font-size: 0.75rem;
      color: #aaa;
      min-height: 1.2em;
      margin: 6px 0;
      text-align: center;
    }
    .row {
      display: flex;
      gap: 8px;
      margin: 4px 0;
      justify-content: center;
    }
    .btn {
      background: #333;
      color: #eee;
      border-radius: 999px;
      border: none;
      padding: 6px 10px;
      font-size: 0.75rem;
      cursor: pointer;
      min-width: 60px;
      transition: background 0.15s, transform 0.08s;
      outline: none;
    }
    .btn:active {
      background: #555;
      transform: scale(0.96);
    }
    .btn--round {
      width: 42px;
      height: 42px;
      border-radius: 50%;
      padding: 0;
      font-size: 1rem;
    }
    .btn--primary {
      background: #4a7dff;
    }
    .btn--primary:active {
      background: #345ad1;
    }
    .dpad-row {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 18px;
      margin: 3px 0;
    }
    .footer {
      font-size: 0.7rem;
      color: #777;
      text-align: center;
      margin-top: 10px;
    }
  </style>
</head>
<body>
  <div class="app">
    <h1>TVHub Remote</h1>
    <div class="subtitle">Select a device, then use the controls</div>

    <div class="label">Device</div>
    <select id="deviceSelect" onchange="onDeviceChange()"></select>

    <div id="status" class="status">Loading devices...</div>

    <!-- Google TV controls -->
    <div id="gtvControls" class="section" style="display:none">
      <div class="label">Google TV Controls</div>
      <div class="row">
        <button class="btn" onclick="sendGTV('BACK')">Back</button>
        <button class="btn btn--primary" onclick="sendGTV('HOME')">Home</button>
      </div>
      <div class="dpad-row">
        <button class="btn btn--round" onclick="sendGTV('UP')">▲</button>
      </div>
      <div class="dpad-row">
        <button class="btn btn--round" onclick="sendGTV('LEFT')">◀</button>
        <button class="btn btn--primary btn--round" onclick="sendGTV('SELECT')">OK</button>
        <button class="btn btn--round" onclick="sendGTV('RIGHT')">▶</button>
      </div>
      <div class="dpad-row">
        <button class="btn btn--round" onclick="sendGTV('DOWN')">▼</button>
      </div>
      <div class="row">
        <button class="btn" onclick="sendGTV('PLAY')">Play</button>
        <button class="btn" onclick="sendGTV('PAUSE')">Pause</button>
        <button class="btn" onclick="sendGTV('STOP')">Stop</button>
      </div>
      <div class="row">
        <button class="btn" onclick="sendGTV('REWIND')">«</button>
        <button class="btn" onclick="sendGTV('FAST_FORWARD')">»</button>
      </div>
      <div class="row">
        <button class="btn" onclick="sendGTV('VOLUME_DOWN')">Vol-</button>
        <button class="btn" onclick="sendGTV('MUTE')">Mute</button>
        <button class="btn" onclick="sendGTV('VOLUME_UP')">Vol+</button>
      </div>
    </div>

    <!-- Hisense controls -->
    <div id="hisenseControls" class="section" style="display:none">
      <div class="label">Hisense TV Volume</div>
      <div class="row">
        <button class="btn" onclick="hisenseStep(-5)">Vol-</button>
        <button class="btn btn--primary" onclick="toggleHisenseMute()">Mute</button>
        <button class="btn" onclick="hisenseStep(5)">Vol+</button>
      </div>
      <div class="label">Volume Slider (0-100)</div>
      <input type="range" id="hisenseVolume" min="0" max="100" value="0" oninput="setHisenseVolume(this.value)">
      <div id="hisenseVolLabel" class="status"></div>
      <div class="row">
        <button class="btn" onclick="refreshHisense()">Refresh status</button>
      </div>
    </div>

    <div class="footer">
      TVHub API – Google TV via ADB, Hisense via UPnP
    </div>
  </div>

<script>
let devices = [];
let current = null;

async function loadDevices() {
  const res = await fetch('/api/devices');
  const data = await res.json();
  devices = data.devices || [];
  const sel = document.getElementById('deviceSelect');
  sel.innerHTML = '';
  devices.forEach(d => {
    const opt = document.createElement('option');
    opt.value = d.id;
    opt.textContent = d.name + ' (' + d.type + ')';
    sel.appendChild(opt);
  });
  if (devices.length > 0) {
    sel.value = devices[0].id;
    current = devices[0];
  }
  onDeviceChange();
}

function onDeviceChange() {
  const sel = document.getElementById('deviceSelect');
  const id = sel.value;
  current = devices.find(d => d.id === id);
  const st = document.getElementById('status');
  const g = document.getElementById('gtvControls');
  const h = document.getElementById('hisenseControls');
  g.style.display = 'none';
  h.style.display = 'none';
  if (!current) {
    st.textContent = 'No device selected';
    return;
  }
  st.textContent = 'Selected ' + current.name + ' (' + current.type + ')';
  if (current.type === 'gtv') {
    g.style.display = 'block';
  } else if (current.type === 'hisense') {
    h.style.display = 'block';
    refreshHisense();
  }
}

async function sendGTV(button) {
  if (!current) return;
  const st = document.getElementById('status');
  st.textContent = 'Sending ' + button + '...';
  const res = await fetch('/api/device/' + encodeURIComponent(current.id) + '/action/button', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({key: button})
  });
  const data = await res.json();
  if (data.ok) {
    st.textContent = 'Sent ' + button;
  } else {
    st.textContent = 'Error: ' + (data.error || 'unknown');
  }
}

async function refreshHisense() {
  if (!current) return;
  const st = document.getElementById('status');
  st.textContent = 'Refreshing volume...';
  const res = await fetch('/api/device/' + encodeURIComponent(current.id) + '/action/get_volume');
  const data = await res.json();
  const volLabel = document.getElementById('hisenseVolLabel');
  if (data.ok) {
    const v = data.volume;
    document.getElementById('hisenseVolume').value = v;
    volLabel.textContent = 'Volume: ' + v;
    st.textContent = 'Hisense status updated';
  } else {
    st.textContent = 'Error: ' + (data.error || 'unknown');
  }
}

async function setHisenseVolume(v) {
  if (!current) return;
  const volLabel = document.getElementById('hisenseVolLabel');
  volLabel.textContent = 'Volume: ' + v + ' (setting...)';
  const res = await fetch('/api/device/' + encodeURIComponent(current.id) + '/action/set_volume', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({volume: v})
  });
  const data = await res.json();
  if (data.ok) {
    volLabel.textContent = 'Volume: ' + data.volume;
  } else {
    volLabel.textContent = 'Error: ' + (data.error || 'unknown');
  }
}

async function hisenseStep(delta) {
  if (!current) return;
  const action = delta > 0 ? 'volume_up' : 'volume_down';
  const res = await fetch('/api/device/' + encodeURIComponent(current.id) + '/action/' + action, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({step: Math.abs(delta)})
  });
  const data = await res.json();
  if (data.ok) {
    document.getElementById('hisenseVolume').value = data.to;
    document.getElementById('hisenseVolLabel').textContent = 'Volume: ' + data.to;
  }
}

async function toggleHisenseMute() {
  if (!current) return;
  const res = await fetch('/api/device/' + encodeURIComponent(current.id) + '/action/toggle_mute', {
    method: 'POST'
  });
  const data = await res.json();
  const st = document.getElementById('status');
  if (data.ok) {
    st.textContent = 'Mute: ' + (data.to ? 'ON' : 'OFF');
  } else {
    st.textContent = 'Error: ' + (data.error || 'unknown');
  }
}

window.addEventListener('load', loadDevices);
</script>
</body>
</html>
"""


@app.route("/")
@app.route("/remote")
def remote():
    return render_template_string(REMOTE_HTML)


@app.route("/api/devices")
def api_devices():
    # Always reload in case discovery has updated devices.json
    refresh_registry()

    ds = [
        {
            "id": d.id,
            "name": d.name,
            "type": d.type,
            "address": d.address,
            "meta": d.meta,
            "actions": list(plugins.get(d.type).actions().keys()) if d.type in plugins else [],
        }
        for d in registry.all()
    ]
    return jsonify({"ok": True, "devices": ds})

@app.route("/api/device/<dev_id>/action/<action>", methods=["GET", "POST"])
def api_action(dev_id, action):
    device = registry.get(dev_id)
    if not device:
        return jsonify({"ok": False, "error": f"Unknown device {dev_id}"}), 404
    plugin = plugins.get(device.type)
    if not plugin:
        return jsonify({"ok": False, "error": f"No plugin for type {device.type}"}), 400

    params: Dict[str, Any] = {}
    if request.method == "GET":
        params.update(request.args)
    else:
        if request.is_json:
            params.update(request.get_json(silent=True) or {})
        params.update(request.args)

    try:
        result = plugin.handle_action(registry, device, action, params)
        code = 200 if result.get("ok") else 500
        return jsonify(result), code
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


def main():
    app.run(host="0.0.0.0", port=10001)


if __name__ == "__main__":
    main()
