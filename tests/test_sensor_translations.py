from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.haier_atw_ew11.sensor import HaierAtwRegisterSensor


class _FakeCoordinator:
    def __init__(
        self,
        raw_by_addr: dict[int, int],
        meta_by_register: dict[int, tuple[float, str]] | None = None,
    ) -> None:
        self.entry = SimpleNamespace(entry_id="entry-1", data={"host": "127.0.0.1"})
        self.data = raw_by_addr
        self._meta_by_register = meta_by_register or {}

    def infer_meta(self, register: int) -> tuple[float, str]:  # noqa: ARG002
        return self._meta_by_register.get(register, (1.0, "uint16"))

    def get_raw_by_register(self, register: int) -> int | None:
        return self.data.get(register - 40001)


def test_sensor_exposes_czech_enum_labels_and_descriptions() -> None:
    point = {
        "register": 40101,
        "ha_address": 100,
        "function": "On-off state",
        "description": "0- Off 1-On",
        "rw": "R",
    }
    coordinator = _FakeCoordinator({100: 1})
    entity = HaierAtwRegisterSensor(coordinator, point)

    attrs = entity.extra_state_attributes
    assert attrs["description"] == "0- Off 1-On"
    assert attrs["description_cs"] == "Stav zapnuti jednotky."
    assert attrs["value_label"] == "On"
    assert attrs["value_label_cs"] == "Zapnuto"
    assert attrs["value_options"]["0"] == "Off"
    assert attrs["value_options_cs"]["0"] == "Vypnuto"


def test_sensor_scales_modbus_raw_value_for_compressor_frequency() -> None:
    point = {
        "register": 40159,
        "ha_address": 158,
        "function": "Compressor frequency",
        "description": "Unit :0.1hz. Sent value = actual value x 10,16 interger",
        "rw": "R",
        "unit": "Hz",
        "scale": 0.1,
        "dtype": "uint16",
    }
    coordinator = _FakeCoordinator(
        raw_by_addr={158: 423},
        meta_by_register={40159: (0.1, "uint16")},
    )
    entity = HaierAtwRegisterSensor(coordinator, point)

    assert entity.native_value == pytest.approx(42.3)


def test_sensor_interprets_signed_int16_from_modbus() -> None:
    point = {
        "register": 40161,
        "ha_address": 160,
        "function": "Compressor discharge temperature",
        "description": "Unit 0.1 C",
        "rw": "R",
        "unit": "C",
        "scale": 0.1,
        "dtype": "int16",
    }
    coordinator = _FakeCoordinator(
        raw_by_addr={160: 0xFF9C},  # -100 in int16
        meta_by_register={40161: (0.1, "int16")},
    )
    entity = HaierAtwRegisterSensor(coordinator, point)

    assert entity.native_value == -10.0


def test_fault_register_sensor_exposes_raw_and_hex() -> None:
    point = {
        "register": 40205,
        "ha_address": 204,
        "function": "Current fault code",
        "description": "Current outdoor unit fault code",
        "rw": "R",
    }
    coordinator = _FakeCoordinator(raw_by_addr={204: 26})
    entity = HaierAtwRegisterSensor(coordinator, point)

    attrs = entity.extra_state_attributes
    assert attrs["raw"] == 26
    assert attrs["hex"] == "0x1a"
