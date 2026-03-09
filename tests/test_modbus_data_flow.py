from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.haier_atw_ew11.coordinator import HaierAtwCoordinator
from custom_components.haier_atw_ew11.sensor import HaierAtwRegisterSensor
from tests.mocks import FakeModbusClient


class _CoordinatorReadHarness:
    def __init__(self, *, use_absolute_addressing: bool, points: list[dict], client: FakeModbusClient) -> None:
        self._use_absolute_addressing = use_absolute_addressing
        self.points = points
        self.client = client

    def register_to_address(self, register: int) -> int:
        return int(register) if self._use_absolute_addressing else int(register) - 40001

    def address_to_register(self, address: int) -> int:
        return int(address) if self._use_absolute_addressing else int(address) + 40001


class _SensorCoordinator:
    def __init__(
        self,
        data_by_register: dict[int, int],
        meta_by_register: dict[int, tuple[float, str]],
    ) -> None:
        self.entry = SimpleNamespace(entry_id="entry-1", data={"host": "127.0.0.1"})
        self._data = data_by_register
        self._meta_by_register = meta_by_register

    def get_raw_by_register(self, register: int) -> int | None:
        return self._data.get(register)

    def infer_meta(self, register: int) -> tuple[float, str]:
        return self._meta_by_register.get(register, (1.0, "uint16"))


@pytest.mark.asyncio
async def test_modbus_absolute_address_read_is_interpreted_as_scaled_frequency() -> None:
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
    harness = _CoordinatorReadHarness(
        use_absolute_addressing=True,
        points=[point],
        client=FakeModbusClient({40159: 423}),
    )

    data = await HaierAtwCoordinator._async_update_data(harness)

    sensor_coordinator = _SensorCoordinator(
        data_by_register=data,
        meta_by_register={40159: (0.1, "uint16")},
    )
    entity = HaierAtwRegisterSensor(sensor_coordinator, point)

    assert data[40159] == 423
    assert entity.native_value == pytest.approx(42.3)


@pytest.mark.asyncio
async def test_modbus_absolute_address_read_is_interpreted_as_signed_temperature() -> None:
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
    harness = _CoordinatorReadHarness(
        use_absolute_addressing=True,
        points=[point],
        client=FakeModbusClient({40161: 0xFF9C}),  # -100 in int16
    )

    data = await HaierAtwCoordinator._async_update_data(harness)

    sensor_coordinator = _SensorCoordinator(
        data_by_register=data,
        meta_by_register={40161: (0.1, "int16")},
    )
    entity = HaierAtwRegisterSensor(sensor_coordinator, point)

    assert data[40161] == 0xFF9C
    assert entity.native_value == -10.0
