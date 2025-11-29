from __future__ import annotations
import importlib
import pkgutil
from typing import Dict, Type

from ..registry import DeviceRegistry, Device

class PluginBase:
    """Base class plugins should subclass."""
    type: str = "base"
    friendly_name: str = "Base Plugin"

    def discover(self, registry: DeviceRegistry) -> None:
        """Discover devices of this type and upsert them into registry."""
        raise NotImplementedError

    def actions(self) -> Dict[str, str]:
        '''Return mapping of action name -> description.'''
        return {}

    def handle_action(self, registry: DeviceRegistry, device: Device, action: str, params):
        """Perform an action on a device."""
        raise NotImplementedError


def load_plugins() -> Dict[str, PluginBase]:
    import tvhub.plugins as pkg
    plugin_map: Dict[str, PluginBase] = {}
    for _, mod_name, _ in pkgutil.iter_modules(pkg.__path__):
        if mod_name.startswith("_"):
            continue
        module = importlib.import_module(f"tvhub.plugins.{mod_name}")
        for attr in dir(module):
            obj = getattr(module, attr)
            if isinstance(obj, type) and issubclass(obj, PluginBase) and obj is not PluginBase:
                plugin = obj()
                plugin_map[plugin.type] = plugin
    return plugin_map
