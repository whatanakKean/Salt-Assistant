import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class InventoryError(ValueError):
    pass


@dataclass(frozen=True)
class Device:
    name: str
    hostname: str
    vendor: str
    platform: str
    role: str
    management_ip: str
    interfaces: tuple[dict[str, str], ...]


class Inventory:
    def __init__(self, devices: list[Device]):
        self.devices = devices

    @classmethod
    def from_file(cls, path: Path) -> "Inventory":
        try:
            data: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as error:
            raise InventoryError(f"Could not read inventory {path}: {error}") from error
        if not isinstance(data, dict) or not isinstance(data.get("devices"), list):
            raise InventoryError("Inventory must contain a devices list")
        devices = []
        for item in data["devices"]:
            if not isinstance(item, dict):
                raise InventoryError("Each inventory device must be a mapping")
            required = ("name", "hostname", "vendor", "platform", "role", "management_ip")
            missing = [field for field in required if not item.get(field)]
            if missing:
                raise InventoryError(f"Device is missing fields: {', '.join(missing)}")
            interfaces = item.get("interfaces", [])
            if not isinstance(interfaces, list) or not all(isinstance(interface, dict) for interface in interfaces):
                raise InventoryError(f"Device {item['name']} has invalid interfaces")
            devices.append(Device(
                name=str(item["name"]), hostname=str(item["hostname"]), vendor=str(item["vendor"]),
                platform=str(item["platform"]), role=str(item["role"]), management_ip=str(item["management_ip"]),
                interfaces=tuple({str(key): str(value) for key, value in interface.items()} for interface in interfaces),
            ))
        return cls(devices)

    def for_device(self, name: str) -> Device:
        for device in self.devices:
            if device.name == name:
                return device
        raise InventoryError(f"Device not found: {name}")

    def as_json(self) -> str:
        return json.dumps({"devices": [device.__dict__ for device in self.devices]}, indent=2, default=list)
