from __future__ import annotations

import pytest

from tests.mocks import FakeModbusClient


@pytest.mark.asyncio
async def test_read_holding_returns_requested_range() -> None:
    client = FakeModbusClient({100: 10, 101: 20, 102: 30})
    result = await client.read_holding(100, 3)
    assert result == [10, 20, 30]


@pytest.mark.asyncio
async def test_write_register_updates_state() -> None:
    client = FakeModbusClient()
    await client.write_register(5, 42)
    assert client.registers[5] == 42


@pytest.mark.asyncio
async def test_read_and_write_failures_raise_timeout() -> None:
    client = FakeModbusClient()
    client.fail_reads = True
    client.fail_writes = True

    with pytest.raises(TimeoutError):
        await client.read_holding(0, 1)

    with pytest.raises(TimeoutError):
        await client.write_register(0, 1)
