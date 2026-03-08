from __future__ import annotations

from homeassistant.components.select import SelectEntity

from .const import MODE_OPTIONS, SPECIAL
from .entity_base import HaierAtwEntity


class HaierAtwModeSelect(HaierAtwEntity, SelectEntity):
    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "mode")
        special_map = getattr(coordinator, "special", SPECIAL)
        spec = special_map["mode"]
        self._reg = spec["register"]
        self._verify = spec["verify_register"]
        self._mode_options = dict(getattr(coordinator, "mode_options", MODE_OPTIONS))
        self._attr_options = list(self._mode_options.values())
        self._attr_unique_id = f"{coordinator.entry.entry_id}_mode"
        self._attr_name = "Mode"

    @property
    def current_option(self) -> str | None:
        raw = self.coordinator.get_raw_by_register(self._verify)
        if raw is None:
            return None
        return self._mode_options.get(int(raw))

    async def async_select_option(self, option: str) -> None:
        inv = {v: k for k, v in self._mode_options.items()}
        if option not in inv:
            raise ValueError(f"Invalid option '{option}'. Expected one of: {', '.join(self.options)}")
        value = inv[option]
        await self.coordinator.client.write_register(
            self.coordinator.register_to_address(self._reg),
            int(value),
        )
        await self.coordinator.async_request_refresh()

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["haier_atw_ew11"][entry.entry_id]
    special_map = getattr(coordinator, "special", SPECIAL)
    if "mode" in special_map:
        async_add_entities([HaierAtwModeSelect(coordinator)])
    else:
        async_add_entities([])
