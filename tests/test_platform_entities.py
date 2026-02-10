from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.components.climate.const import HVACMode

from custom_components.haier_atw_ew11.climate import HaierAtwClimate
from custom_components.haier_atw_ew11.number import HaierAtwSetpointNumber
from custom_components.haier_atw_ew11.select import HaierAtwModeSelect
from custom_components.haier_atw_ew11.switch import HaierAtwSwitch
from tests.mocks import FakeModbusClient


class _FakeCoordinator:
    def __init__(self, raw_by_addr: dict[int, int] | None = None) -> None:
        self.entry = SimpleNamespace(entry_id="entry-1", data={"host": "127.0.0.1"})
        self.client = FakeModbusClient()
        self.data = raw_by_addr or {}
        self.async_request_refresh = AsyncMock()

    def get_raw_by_register(self, register: int) -> int | None:
        return self.data.get(register - 40001)

    def infer_meta(self, register: int) -> tuple[float, str]:  # noqa: ARG002
        # 40142 in points.json is typically temperature in 0.1 units.
        return 0.1, "int16"


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
