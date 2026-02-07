from __future__ import annotations

from homeassistant.components.select import SelectEntity

from .const import SPECIAL, MODE_OPTIONS
from .entity_base import HaierAtwEntity


class HaierAtwModeSelect(HaierAtwEntity, SelectEntity):
    _attr_options = list(MODE_OPTIONS.values())

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "mode")
        self._reg = SPECIAL["mode"]["register"]
        self._verify = SPECIAL["mode"]["verify_register"]
        self._attr_unique_id = f"{coordinator.entry.entry_id}_mode"
        self._attr_name = "Mode"

    @property
    def current_option(self) -> str | None:
        raw = self.coordinator.get_raw_by_register(self._verify)
        if raw is None:
            return None
        return MODE_OPTIONS.get(int(raw))

    async def async_select_option(self, option: str) -> None:
        inv = {v: k for k, v in MODE_OPTIONS.items()}
        if option not in inv:
            raise ValueError(f"Invalid option '{option}'. Expected one of: {', '.join(self.options)}")
        value = inv[option]
        await self.coordinator.client.write_register(self._reg - 40001, int(value))
        await self.coordinator.async_request_refresh()

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["haier_atw_ew11"][entry.entry_id]
    async_add_entities([HaierAtwModeSelect(coordinator)])
