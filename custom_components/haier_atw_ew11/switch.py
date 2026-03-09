from __future__ import annotations

from homeassistant.components.switch import SwitchEntity

from .const import SPECIAL
from .entity_base import HaierAtwEntity


class HaierAtwSwitch(HaierAtwEntity, SwitchEntity):
    def __init__(self, coordinator, key: str, name: str) -> None:
        super().__init__(coordinator, key)
        special_map = getattr(coordinator, "special", SPECIAL)
        spec = special_map[key]
        self._reg = spec["register"]
        self._verify = spec["verify_register"]
        self._on_value = int(spec.get("on_value", 1))
        self._off_value = int(spec.get("off_value", 0))
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_name = name

    @property
    def is_on(self) -> bool | None:
        raw = self.coordinator.get_raw_by_register(self._verify)
        if raw is None:
            return None
        return int(raw) == self._on_value

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.client.write_register(
            self.coordinator.register_to_address(self._reg),
            self._on_value,
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.client.write_register(
            self.coordinator.register_to_address(self._reg),
            self._off_value,
        )
        await self.coordinator.async_request_refresh()

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["haier_atw_ew11"][entry.entry_id]
    special_map = getattr(coordinator, "special", SPECIAL)
    entities = []
    if "power" in special_map:
        entities.append(HaierAtwSwitch(coordinator, "power", "Power"))
    if "eco" in special_map:
        entities.append(HaierAtwSwitch(coordinator, "eco", "ECO"))
    if "fast_dhw" in special_map:
        entities.append(HaierAtwSwitch(coordinator, "fast_dhw", "Fast DHW"))
    async_add_entities(entities)
