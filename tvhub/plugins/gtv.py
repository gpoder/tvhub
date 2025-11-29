from __future__ import annotations
import subprocess
from typing import Dict, Any, List

from zeroconf import Zeroconf, ServiceBrowser, ServiceListener, ServiceInfo

from . import PluginBase
from ..registry import DeviceRegistry, Device
from ..config import ADB_BIN

SERVICE = "_adb-tls-connect._tcp.local."

class _GtvListener(ServiceListener):
    def __init__(self):
        self.found: Dict[str, ServiceInfo] = {}

    def remove_service(self, zc, type_, name):
        self.found.pop(name, None)

    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info:
            self.found[name] = info

    def update_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info:
            self.found[name] = info

class GoogleTVPlugin(PluginBase):
    type = "gtv"
    friendly_name = "Google TV (ADB)"

    KEYCODES = {
        "HOME": 3,
        "BACK": 4,
        "UP": 19,
        "DOWN": 20,
        "LEFT": 21,
        "RIGHT": 22,
        "SELECT": 23,
        "ENTER": 66,
        "PLAY": 126,
        "PAUSE": 127,
        "STOP": 86,
        "NEXT": 87,
        "PREVIOUS": 88,
        "REWIND": 89,
        "FAST_FORWARD": 90,
        "MUTE": 164,
        "VOLUME_UP": 24,
        "VOLUME_DOWN": 25,
        "0": 7,
        "1": 8,
        "2": 9,
        "3": 10,
        "4": 11,
        "5": 12,
        "6": 13,
        "7": 14,
        "8": 15,
        "9": 16,
    }

    def discover(self, registry: DeviceRegistry) -> None:
        zc = Zeroconf()
        listener = _GtvListener()
        browser = ServiceBrowser(zc, SERVICE, listener)
        import time
        time.sleep(3)
        zc.close()

        for name, info in listener.found.items():
            if not info.addresses:
                continue
            ip_bytes = info.addresses[0]
            ip = ".".join(map(str, ip_bytes))
            port = info.port
            dev_id = name.split(".")[0]  # e.g. adb-XXXX
            device = Device(
                id=dev_id,
                name=dev_id,
                type=self.type,
                address=f"{ip}:{port}",
                meta={"raw_name": name},
            )
            registry.upsert(device)

    def actions(self) -> Dict[str, str]:
        return {
            "button": "Send a remote button by name or keycode",
            "text": "Send text input",
            "keyevent": "Send a raw numeric keyevent",
            "status": "Basic adb shell dumpsys activity activities",
        }

    # --- internal helpers ---

    def _adb(self, addr: str, args: List[str]) -> subprocess.CompletedProcess:
        cmd = [ADB_BIN, "-s", addr] + args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5)

    def _button(self, device: Device, name: str) -> Dict[str, Any]:
        name = name.upper()
        if name in self.KEYCODES:
            code = self.KEYCODES[name]
        elif name.isdigit():
            code = int(name)
        else:
            return {"ok": False, "error": "Unknown key", "input": name}
        # connect
        subprocess.run([ADB_BIN, "connect", device.address], capture_output=True, text=True, timeout=5)
        res = self._adb(device.address, ["shell", "input", "keyevent", str(code)])
        ok = (res.returncode == 0)
        return {"ok": ok, "code": code, "stdout": res.stdout, "stderr": res.stderr}

    def _text(self, device: Device, text: str) -> Dict[str, Any]:
        subprocess.run([ADB_BIN, "connect", device.address], capture_output=True, text=True, timeout=5)
        res = self._adb(device.address, ["shell", "input", "text", text.replace(" ", "%s")])
        ok = (res.returncode == 0)
        return {"ok": ok, "stdout": res.stdout, "stderr": res.stderr}

    def _status(self, device: Device) -> Dict[str, Any]:
        subprocess.run([ADB_BIN, "connect", device.address], capture_output=True, text=True, timeout=5)
        res = self._adb(device.address, ["shell", "dumpsys", "activity", "activities"])
        ok = (res.returncode == 0)
        top = None
        if ok:
            for line in res.stdout.splitlines():
                line = line.strip()
                if "ResumedActivity:" in line or "topResumedActivity=" in line:
                    top = line
                    break
        return {"ok": ok, "top": top, "stdout": res.stdout[:4000], "stderr": res.stderr}

    def handle_action(self, registry: DeviceRegistry, device: Device, action: str, params):
        if action == "button":
            return self._button(device, params.get("key", "HOME"))
        if action == "keyevent":
            return self._button(device, str(params.get("code", "3")))
        if action == "text":
            return self._text(device, params.get("text", ""))
        if action == "status":
            return self._status(device)
        return {"ok": False, "error": f"Unknown action {action}"}
