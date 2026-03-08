from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.components.climate.const import HVACMode

from custom_components.haier_atw_ew11.climate import HaierAtwClimate
from custom_components.haier_atw_ew11.const import MODE_OPTIONS, SPECIAL
from custom_components.haier_atw_ew11.number import HaierAtwSetpointNumber
from custom_components.haier_atw_ew11.select import HaierAtwModeSelect
from custom_components.haier_atw_ew11.switch import HaierAtwSwitch
from tests.mocks import FakeModbusClient


class _FakeCoordinator:
    def __init__(
        self,
        raw_by_addr: dict[int, int] | None = None,
        *,
        register_base: int = 40001,
        special: dict[str, dict] | None = None,
        mode_options: dict[int, str] | None = None,
        mode_to_hvac: dict[int, str] | None = None,
        hvac_to_mode: dict[str, int] | None = None,
        current_temperature_register: int = 40142,
    ) -> None:
        self.entry = SimpleNamespace(entry_id="entry-1", data={"host": "127.0.0.1"})
        self.client = FakeModbusClient()
        self.data = raw_by_addr or {}
        self.special = special or SPECIAL
        self.mode_options = mode_options or MODE_OPTIONS
        self.mode_to_hvac = mode_to_hvac or {
            0: "auto",
            1: "cool",
            2: "heat",
            5: "heat",
            6: "auto",
            7: "cool",
            8: "heat",
        }
        self.hvac_to_mode = hvac_to_mode or {"auto": 0, "cool": 1, "heat": 2}
        self.current_temperature_register = current_temperature_register
        self._register_base = register_base
        self.async_request_refresh = AsyncMock()

    def get_raw_by_register(self, register: int) -> int | None:
        return self.data.get(register - self._register_base)

    def infer_meta(self, register: int) -> tuple[float, str]:  # noqa: ARG002
        # 40142 in points.json is typically temperature in 0.1 units.
        return 0.1, "int16"

    def register_to_address(self, register: int) -> int:
        return int(register) - self._register_base


@pytest.mark.asyncio
async def test_switch_reads_and_writes_registers() -> None:
    coordinator = _FakeCoordinator({100: 0})  # 40101
    entity = HaierAtwSwitch(coordinator, "power", "Power")

    assert entity.is_on is False
    await entity.async_turn_on()
    await entity.async_turn_off()

    assert coordinator.client.registers[0] == 0  # 40001 address
    assert coordinator.async_request_refresh.await_count == 2


@pytest.mark.asyncio
async def test_mode_select_reads_validates_and_writes() -> None:
    coordinator = _FakeCoordinator({101: 2})  # 40102 -> Heat
    entity = HaierAtwModeSelect(coordinator)

    assert entity.current_option == "Heat"

    with pytest.raises(ValueError):
        await entity.async_select_option("Invalid")

    await entity.async_select_option("DHW")
    assert coordinator.client.registers[1] == 3  # 40002 address, DHW value
    coordinator.async_request_refresh.assert_awaited()


@pytest.mark.asyncio
async def test_setpoint_number_reads_scaled_value_and_writes_scaled_raw() -> None:
    coordinator = _FakeCoordinator({102: 32})  # 40103 verify for zone1
    entity = HaierAtwSetpointNumber(coordinator, "zone1_sp", "ZONE1 setpoint")

    assert entity.native_value == 16.0
    await entity.async_set_native_value(15.5)

    assert coordinator.client.registers[2] == 31  # 40003 address, scale_write=2.0
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_climate_entity_reads_and_controls_main_registers() -> None:
    coordinator = _FakeCoordinator(
        {
            100: 1,   # 40101 power status
            101: 2,   # 40102 mode status -> Heat
            102: 32,  # 40103 target -> 16.0C
            141: 330, # 40142 current -> 33.0C
        }
    )
    entity = HaierAtwClimate(coordinator)

    assert entity.hvac_mode == HVACMode.HEAT
    assert entity.target_temperature == 16.0
    assert entity.current_temperature == 33.0

    await entity.async_set_temperature(temperature=15.5)
    assert coordinator.client.registers[2] == 31  # 40003 addr

    await entity.async_set_hvac_mode(HVACMode.COOL)
    assert coordinator.client.registers[0] == 1   # 40001 power on
    assert coordinator.client.registers[1] == 1   # 40002 cool mode

    await entity.async_set_hvac_mode(HVACMode.OFF)
    assert coordinator.client.registers[0] == 0   # 40001 power off


@pytest.mark.asyncio
async def test_compact_profile_power_and_mode_are_interpreted_correctly() -> None:
    compact_special = {
        "power": {"register": 4, "verify_register": 4, "on_value": 0, "off_value": 1},
        "mode": {"register": 5, "verify_register": 5},
        "zone1_sp": {"register": 6, "verify_register": 6, "scale_write": 10.0, "scale_read": 0.1, "step": 0.5, "min": 5, "max": 60},
    }
    coordinator = _FakeCoordinator(
        {
            4: 0,    # on
            5: 0,    # heat
            6: 205,  # 20.5 C
            8: 198,  # current temperature register
        },
        register_base=0,
        special=compact_special,
        mode_options={0: "Heat", 1: "Cool"},
        mode_to_hvac={0: "heat", 1: "cool"},
        hvac_to_mode={"heat": 0, "cool": 1},
        current_temperature_register=8,
    )

    switch = HaierAtwSwitch(coordinator, "power", "Power")
    climate = HaierAtwClimate(coordinator)

    assert switch.is_on is True
    assert climate.hvac_mode == HVACMode.HEAT
    assert climate.target_temperature == 20.5
    assert climate.current_temperature == 19.8

    await switch.async_turn_off()
    assert coordinator.client.registers[4] == 1  # compact off value
