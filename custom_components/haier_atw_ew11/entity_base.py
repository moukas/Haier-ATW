from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HaierAtwCoordinator


class HaierAtwEntity(CoordinatorEntity[HaierAtwCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: HaierAtwCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key

    @property
    def device_info(self) -> DeviceInfo:
        entry = self.coordinator.entry
        return DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Haier ATW ({entry.data.get('host')})",
            manufacturer="Haier",
            model="ATW via EW11",
        )
