from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, Optional, List

from .config import DEVICES_FILE, DATA_DIR

@dataclass
class Device:
    id: str
    name: str
    type: str   # e.g. 'gtv' or 'hisense'
    address: str  # e.g. 'ip:port' or 'ip'
    meta: Dict[str, Any]

class DeviceRegistry:
    def __init__(self, path: Path = DEVICES_FILE):
        self.path = path
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.devices: Dict[str, Device] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.devices = {}
            return
        try:
            data = json.loads(self.path.read_text())
            self.devices = {
                k: Device(**v) for k, v in data.items()
            }
        except Exception:
            self.devices = {}

    def save(self) -> None:
        data = {k: asdict(v) for k, v in self.devices.items()}
        self.path.write_text(json.dumps(data, indent=2))

    def all(self) -> List[Device]:
        return list(self.devices.values())

    def get(self, dev_id: str) -> Optional[Device]:
        return self.devices.get(dev_id)

    def upsert(self, device: Device) -> None:
        self.devices[device.id] = device
        self.save()

    def remove_type(self, dev_type: str) -> None:
        self.devices = {k: v for k, v in self.devices.items() if v.type != dev_type}
        self.save()
