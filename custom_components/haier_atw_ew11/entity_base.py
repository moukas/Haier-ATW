from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME, DEFAULT_NAME, DOMAIN
from .coordinator import HaierAtwCoordinator


class HaierAtwEntity(CoordinatorEntity[HaierAtwCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: HaierAtwCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key

    @property
    def device_info(self) -> DeviceInfo:
        entry = self.coordinator.entry
        configured_name = str(entry.data.get(CONF_NAME) or "").strip()
        return DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=configured_name or DEFAULT_NAME,
            manufacturer="Haier",
            model="ATW via EW11",
        )
