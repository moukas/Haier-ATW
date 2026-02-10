from __future__ import annotations

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature

from .const import REGISTER_BASE, SPECIAL
from .entity_base import HaierAtwEntity


_MODE_TO_HVAC: dict[int, HVACMode] = {
    0: HVACMode.AUTO,
    1: HVACMode.COOL,
    2: HVACMode.HEAT,
    5: HVACMode.HEAT,
    6: HVACMode.AUTO,
    7: HVACMode.COOL,
    8: HVACMode.HEAT,
}

_HVAC_TO_MODE: dict[HVACMode, int] = {
    HVACMode.AUTO: 0,
    HVACMode.COOL: 1,
    HVACMode.HEAT: 2,
}


class HaierAtwClimate(HaierAtwEntity, ClimateEntity):
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.AUTO, HVACMode.HEAT, HVACMode.COOL]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "climate_zone1")
        self._attr_unique_id = f"{coordinator.entry.entry_id}_climate_zone1"
        self._attr_name = "ZONE1 Climate"

        self._power_reg = SPECIAL["power"]["register"]
        self._power_verify = SPECIAL["power"]["verify_register"]
        self._mode_reg = SPECIAL["mode"]["register"]
        self._mode_verify = SPECIAL["mode"]["verify_register"]
        self._setpoint_reg = SPECIAL["zone1_sp"]["register"]
        self._setpoint_verify = SPECIAL["zone1_sp"]["verify_register"]
        self._scale_write = float(SPECIAL["zone1_sp"].get("scale_write", 1.0))
        self._scale_read = float(SPECIAL["zone1_sp"].get("scale_read", 1.0))
        self._attr_target_temperature_step = float(SPECIAL["zone1_sp"].get("step", 1.0))
        self._attr_min_temp = float(SPECIAL["zone1_sp"].get("min", 0))
        self._attr_max_temp = float(SPECIAL["zone1_sp"].get("max", 80))

    @property
    def hvac_mode(self) -> HVACMode | None:
        power = self.coordinator.get_raw_by_register(self._power_verify)
        if power is None:
            return None
        if int(power) == 0:
            return HVACMode.OFF

        mode_raw = self.coordinator.get_raw_by_register(self._mode_verify)
        if mode_raw is None:
            return HVACMode.HEAT
        return _MODE_TO_HVAC.get(int(mode_raw), HVACMode.HEAT)

    @property
    def target_temperature(self) -> float | None:
        raw = self.coordinator.get_raw_by_register(self._setpoint_verify)
        if raw is None:
            return None
        return float(raw) * self._scale_read

    @property
    def current_temperature(self) -> float | None:
        # 40142 is a useful operational water temperature in most deployments.
        raw = self.coordinator.get_raw_by_register(40142)
        if raw is None:
            return None
        scale, dtype = self.coordinator.infer_meta(40142)
        value = int(raw)
        if dtype == "int16" and value >= 0x8000:
            value -= 0x10000
        return float(value) * float(scale)

    async def async_set_temperature(self, **kwargs) -> None:
        if (temperature := kwargs.get("temperature")) is None:
            return
        raw = int(round(float(temperature) * self._scale_write))
        await self.coordinator.client.write_register(self._setpoint_reg - REGISTER_BASE, raw)
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self.async_turn_off()
            return
        if hvac_mode not in _HVAC_TO_MODE:
            raise ValueError(f"Unsupported HVAC mode: {hvac_mode}")

        await self.coordinator.client.write_register(self._power_reg - REGISTER_BASE, 1)
        await self.coordinator.client.write_register(
            self._mode_reg - REGISTER_BASE, _HVAC_TO_MODE[hvac_mode]
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        await self.coordinator.client.write_register(self._power_reg - REGISTER_BASE, 1)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        await self.coordinator.client.write_register(self._power_reg - REGISTER_BASE, 0)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["haier_atw_ew11"][entry.entry_id]
    async_add_entities([HaierAtwClimate(coordinator)])
