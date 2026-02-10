from __future__ import annotations

from types import SimpleNamespace

from custom_components.haier_atw_ew11.sensor import HaierAtwRegisterSensor


class _FakeCoordinator:
    def __init__(self, raw_by_addr: dict[int, int]) -> None:
        self.entry = SimpleNamespace(entry_id="entry-1", data={"host": "127.0.0.1"})
        self.data = raw_by_addr

    def infer_meta(self, register: int) -> tuple[float, str]:  # noqa: ARG002
        return 1.0, "uint16"

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
