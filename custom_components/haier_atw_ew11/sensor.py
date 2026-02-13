from __future__ import annotations

import re

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTemperature

from .entity_base import HaierAtwEntity


_VALUE_LABEL_CS: dict[str, str] = {
    "off": "Vypnuto",
    "on": "Zapnuto",
    "no": "Ne",
    "yes": "Ano",
    "auto": "Automat",
    "cool": "Chlazeni",
    "heat": "Topeni",
    "dhw": "TUV",
    "pool": "Bazen",
    "heating + pool": "Topeni + bazen",
    "auto + dhw": "Automat + TUV",
    "cool + dhw": "Chlazeni + TUV",
    "heat + dhw": "Topeni + TUV",
    "normal": "Normal",
    "quiet": "Tichy",
    "turbo": "Turbo",
}


_POINT_DESCRIPTION_CS: dict[int, str] = {
    40101: "Stav zapnuti jednotky.",
    40102: "Aktualni provozni rezim.",
    40104: "Zpusob rizeni ZONE1.",
    40106: "Zpusob rizeni ZONE2.",
    40110: "Stav ECO rezimu.",
    40111: "Stav Fast DHW.",
}


def _parse_enum_pairs(desc: str) -> dict[int, str]:
    # Supports forms like "0- Off 1-On" and "0- Auto, 1- cool, 2- heat".
    pattern = r"(\d+)\s*-\s*(.*?)(?=(?:,\s*\d+\s*-)|(?:\s+\d+\s*-)|$)"
    pairs = re.findall(pattern, desc or "")
    parsed: dict[int, str] = {}
    for value_s, label in pairs:
        cleaned = " ".join(str(label).replace("ďĽŚ", ",").split()).strip(" ,;")
        if not cleaned:
            continue
        parsed[int(value_s)] = cleaned
    return parsed


def _to_czech_label(label: str) -> str:
    normalized = " ".join(label.lower().split())
    return _VALUE_LABEL_CS.get(normalized, label)


class HaierAtwRegisterSensor(HaierAtwEntity, SensorEntity):
    def __init__(self, coordinator, point: dict) -> None:
        key = f"reg_{point['register']}"
        super().__init__(coordinator, key)
        self._point = point
        self._addr = point["ha_address"]
        self._reg = point["register"]
        self._description = str(point.get("description", ""))
        self._enum_map = _parse_enum_pairs(self._description)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_name = point.get("function") or f"Register {self._reg}"

        desc = self._description
        scale, dtype = coordinator.infer_meta(self._reg)
        self._scale = scale
        self._dtype = dtype

        unit = point.get("unit")
        if unit:
            unit_l = str(unit).lower()
            if any(token in unit_l for token in ("°c", "℃", "â„ƒ", "Â°c".lower())):
                self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
                self._attr_device_class = SensorDeviceClass.TEMPERATURE
            else:
                self._attr_native_unit_of_measurement = str(unit)

        # Unit detection fallback from description.
        if not getattr(self, "_attr_native_unit_of_measurement", None):
            desc_l = desc.lower()
            if any(token in desc_l for token in ("°c", "℃", "â„ƒ", "Â°c".lower())):
                self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
                self._attr_device_class = SensorDeviceClass.TEMPERATURE
            elif "hz" in desc_l:
                self._attr_native_unit_of_measurement = "Hz"

    @property
    def native_value(self):
        raw = self.coordinator.get_raw_by_register(self._reg)
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
        attrs = {
            "register": self._reg,
            "description": self._description,
        }
        description_cs = _POINT_DESCRIPTION_CS.get(self._reg)
        if description_cs:
            attrs["description_cs"] = description_cs

        raw = self.coordinator.get_raw_by_register(self._reg)
        if raw is not None and self._enum_map:
            label_en = self._enum_map.get(int(raw))
            if label_en is not None:
                attrs["value_label"] = label_en
                attrs["value_label_cs"] = _to_czech_label(label_en)
            attrs["value_options"] = {str(k): v for k, v in self._enum_map.items()}
            attrs["value_options_cs"] = {
                str(k): _to_czech_label(v) for k, v in self._enum_map.items()
            }

        # Provide helpful attributes for fault registers.
        if self._reg in (40204, 40205):
            if raw is None:
                return attrs
            attrs["raw"] = raw
            attrs["hex"] = hex(int(raw))
        return attrs


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["haier_atw_ew11"][entry.entry_id]
    entities = []
    for p in coordinator.points:
        rw = p.get("rw") or ""
        if "R" not in rw:
            continue
        entities.append(HaierAtwRegisterSensor(coordinator, p))
    async_add_entities(entities)
