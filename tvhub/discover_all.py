#!/usr/bin/env python3
"""Run discovery for all plugins and update the registry.

You can call this from a systemd timer.
"""
from .registry import DeviceRegistry
from .plugins import load_plugins

def main():
    reg = DeviceRegistry()
    plugins = load_plugins()
    # Clear types we will re-discover
    for t in plugins.keys():
        reg.remove_type(t)

    for t, plugin in plugins.items():
        try:
            plugin.discover(reg)
        except Exception as e:
            print(f"Discovery failed for {t}: {e}")

if __name__ == "__main__":
    main()
