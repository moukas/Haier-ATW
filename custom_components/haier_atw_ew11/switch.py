from __future__ import annotations

from homeassistant.components.switch import SwitchEntity

from .const import SPECIAL
from .entity_base import HaierAtwEntity


class HaierAtwSwitch(HaierAtwEntity, SwitchEntity):
    def __init__(self, coordinator, key: str, name: str) -> None:
        super().__init__(coordinator, key)
        self._reg = SPECIAL[key]["register"]
        self._verify = SPECIAL[key]["verify_register"]
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_name = name

    @property
    def is_on(self) -> bool | None:
        raw = self.coordinator.get_raw_by_register(self._verify)
        if raw is None:
            return None
        return int(raw) == 1

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.client.write_register(
            self.coordinator.register_to_address(self._reg),
            1,
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.client.write_register(
            self.coordinator.register_to_address(self._reg),
            0,
        )
        await self.coordinator.async_request_refresh()

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["haier_atw_ew11"][entry.entry_id]
    async_add_entities([
        HaierAtwSwitch(coordinator, "power", "Power"),
        HaierAtwSwitch(coordinator, "eco", "ECO"),
        HaierAtwSwitch(coordinator, "fast_dhw", "Fast DHW"),
    ])
