from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import UnitOfTemperature

from .entity_base import HaierAtwEntity


class HaierAtwRegisterSensor(HaierAtwEntity, SensorEntity):
    def __init__(self, coordinator, point: dict) -> None:
        key = f"reg_{point['register']}"
        super().__init__(coordinator, key)
        self._point = point
        self._addr = point["ha_address"]
        self._reg = point["register"]
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_name = point.get("function") or f"Register {self._reg}"

        desc = point.get("description", "")
        scale, dtype = coordinator.infer_meta(self._reg)
        self._scale = scale
        self._dtype = dtype

        unit = point.get('unit')
        if unit:
            self._attr_native_unit_of_measurement = unit
            if unit in ('°C','℃'):
                self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
                self._attr_device_class = SensorDeviceClass.TEMPERATURE
        
        # unit detection (explicit metadata preferred)
        if not getattr(self, '_attr_native_unit_of_measurement', None) and ("℃" in desc or "°c" in desc.lower()):
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
        elif not getattr(self, '_attr_native_unit_of_measurement', None) and "hz" in desc.lower():
            self._attr_native_unit_of_measurement = "Hz"

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.get(self._addr)
        if raw is None:
            return None
        # int16 handling if needed
        if self._dtype == "int16":
            v = int(raw)
            if v >= 0x8000:
                v = v - 0x10000
            return v * self._scale
        return int(raw) * self._scale


    @property
    def extra_state_attributes(self):
        # Provide helpful attributes for fault registers.
        if self._reg in (40204, 40205):
            raw = self.coordinator.get_raw_by_register(self._reg)
            if raw is None:
                return None
            return {
                "register": self._reg,
                "raw": raw,
                "hex": hex(int(raw)),
            }
        return {"register": self._reg}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["haier_atw_ew11"][entry.entry_id]
    # create sensors for all readable points (R or R/W), excluding verify registers that are better represented by special entities? We'll keep all.
    entities = []
    for p in coordinator.points:
        rw = (p.get("rw") or "")
        if "R" not in rw:
            continue
        entities.append(HaierAtwRegisterSensor(coordinator, p))
    async_add_entities(entities)
