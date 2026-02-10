from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.const import UnitOfTemperature

from .const import REGISTER_BASE, SPECIAL
from .entity_base import HaierAtwEntity


class HaierAtwSetpointNumber(HaierAtwEntity, NumberEntity):
    def __init__(self, coordinator, key: str, name: str) -> None:
        super().__init__(coordinator, key)
        spec = SPECIAL[key]
        self._reg = spec["register"]
        self._verify = spec["verify_register"]
        self._scale_write = float(spec.get("scale_write", 1.0))
        self._scale_read = float(spec.get("scale_read", 1.0))
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_native_min_value = float(spec.get("min", 0))
        self._attr_native_max_value = float(spec.get("max", 80))
        self._attr_native_step = float(spec.get("step", 1.0))
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> float | None:
        raw = self.coordinator.get_raw_by_register(self._verify)
        if raw is None:
            return None
        return float(raw) * self._scale_read

    async def async_set_native_value(self, value: float) -> None:
        raw = int(round(float(value) * self._scale_write))
        await self.coordinator.client.write_register(self._reg - REGISTER_BASE, raw)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["haier_atw_ew11"][entry.entry_id]
    async_add_entities(
        [
            HaierAtwSetpointNumber(coordinator, "zone1_sp", "ZONE1 setpoint"),
            HaierAtwSetpointNumber(coordinator, "zone2_sp", "ZONE2 setpoint"),
            HaierAtwSetpointNumber(coordinator, "dhw_sp", "DHW setpoint"),
            HaierAtwSetpointNumber(coordinator, "pool_sp", "Pool setpoint"),
            HaierAtwSetpointNumber(coordinator, "steril_sp", "Sterilization setpoint"),
        ]
    )
