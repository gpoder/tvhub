from __future__ import annotations
import xml.etree.ElementTree as ET
from typing import Dict, Any

import requests

from . import PluginBase
from ..registry import DeviceRegistry, Device
from ..config import HISENSE_DMR_PORT, HISENSE_INSTANCE_ID, HISENSE_CHANNEL

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
RCS_URN = "urn:schemas-upnp-org:service:RenderingControl:1"

def _soap_envelope(action: str, body_xml: str) -> str:
    return f"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="{SOAP_NS}">
  <s:Body>
    <u:{action} xmlns:u="{RCS_URN}">
      {body_xml}
    </u:{action}>
  </s:Body>
</s:Envelope>
"""

def _control_url(ip: str) -> str:
    return f"http://{ip}:{HISENSE_DMR_PORT}/control/RenderingControl"

def _post(ip: str, action: str, body_xml: str) -> requests.Response:
    envelope = _soap_envelope(action, body_xml)
    headers = {
        "Content-Type": "text/xml; charset=\"utf-8\"",
        "SOAPACTION": f"\"{RCS_URN}#{action}\"",
    }
    url = _control_url(ip)
    resp = requests.post(url, data=envelope.encode("utf-8"), headers=headers, timeout=3)
    resp.raise_for_status()
    return resp

def hisense_get_volume(ip: str) -> int:
    body = f"""
      <InstanceID>{HISENSE_INSTANCE_ID}</InstanceID>
      <Channel>{HISENSE_CHANNEL}</Channel>
    """
    resp = _post(ip, "GetVolume", body)
    root = ET.fromstring(resp.text)
    volume = 0
    for elem in root.findall(".//CurrentVolume"):
        try:
            volume = int(elem.text)
        except Exception:
            volume = 0
    return volume

def hisense_set_volume(ip: str, vol: int) -> None:
    vol = max(0, min(100, int(vol)))
    body = f"""
      <InstanceID>{HISENSE_INSTANCE_ID}</InstanceID>
      <Channel>{HISENSE_CHANNEL}</Channel>
      <DesiredVolume>{vol}</DesiredVolume>
    """
    _post(ip, "SetVolume", body)

def hisense_get_mute(ip: str) -> bool:
    body = f"""
      <InstanceID>{HISENSE_INSTANCE_ID}</InstanceID>
      <Channel>{HISENSE_CHANNEL}</Channel>
    """
    resp = _post(ip, "GetMute", body)
    root = ET.fromstring(resp.text)
    for elem in root.findall(".//CurrentMute"):
        return elem.text == "1"
    return False

def hisense_set_mute(ip: str, mute: bool) -> None:
    body = f"""
      <InstanceID>{HISENSE_INSTANCE_ID}</InstanceID>
      <Channel>{HISENSE_CHANNEL}</Channel>
      <DesiredMute>{1 if mute else 0}</DesiredMute>
    """
    _post(ip, "SetMute", body)


class HisenseTVPlugin(PluginBase):
    type = "hisense"
    friendly_name = "Hisense TV (UPnP DMR)"

    def discover(self, registry: DeviceRegistry) -> None:
        """Very simple: if user already knows IPs they can seed registry manually.

        We only keep already-registered hisense devices (no active discovery).
        """
        # In future you can add SSDP discovery here; for now we do nothing.
        return

    def actions(self) -> Dict[str, str]:
        return {
            "get_volume": "Get current volume",
            "set_volume": "Set volume 0-100",
            "volume_up": "Increase volume by step",
            "volume_down": "Decrease volume by step",
            "get_mute": "Get mute state",
            "set_mute": "Set mute true/false",
            "toggle_mute": "Toggle mute",
        }

    def handle_action(self, registry: DeviceRegistry, device: Device, action: str, params):
        ip = device.address.split(":")[0]
        step = int(params.get("step", 5))
        try:
            if action == "get_volume":
                v = hisense_get_volume(ip)
                return {"ok": True, "volume": v}
            if action == "set_volume":
                v = int(params.get("volume", 0))
                hisense_set_volume(ip, v)
                return {"ok": True, "volume": v}
            if action == "volume_up":
                cur = hisense_get_volume(ip)
                new = max(0, min(100, cur + step))
                hisense_set_volume(ip, new)
                return {"ok": True, "from": cur, "to": new}
            if action == "volume_down":
                cur = hisense_get_volume(ip)
                new = max(0, min(100, cur - step))
                hisense_set_volume(ip, new)
                return {"ok": True, "from": cur, "to": new}
            if action == "get_mute":
                m = hisense_get_mute(ip)
                return {"ok": True, "mute": m}
            if action == "set_mute":
                v = str(params.get("mute", "false")).lower() in ("1", "true", "yes", "on")
                hisense_set_mute(ip, v)
                return {"ok": True, "mute": v}
            if action == "toggle_mute":
                cur = hisense_get_mute(ip)
                new = not cur
                hisense_set_mute(ip, new)
                return {"ok": True, "from": cur, "to": new}
        except Exception as e:
            return {"ok": False, "error": str(e)}

        return {"ok": False, "error": f"Unknown action {action}"}
