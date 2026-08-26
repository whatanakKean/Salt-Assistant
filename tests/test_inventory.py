from pathlib import Path

import pytest

from salt_assistant.inventory import Inventory, InventoryError


def test_inventory_loads_device(tmp_path: Path):
    path = tmp_path / "devices.yml"
    path.write_text(
        "devices:\n  - name: edge-1\n    hostname: edge-1\n    vendor: cisco\n"
        "    platform: ios\n    role: edge-router\n    management_ip: 192.0.2.10\n",
        encoding="utf-8",
    )
    inventory = Inventory.from_file(path)
    assert inventory.for_device("edge-1").platform == "ios"


def test_inventory_requires_device_fields(tmp_path: Path):
    path = tmp_path / "devices.yml"
    path.write_text("devices:\n  - name: incomplete\n", encoding="utf-8")
    with pytest.raises(InventoryError, match="missing fields"):
        Inventory.from_file(path)