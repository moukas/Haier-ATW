from __future__ import annotations

import asyncio
from dataclasses import dataclass
from inspect import isawaitable

from pymodbus.client import AsyncModbusTcpClient


@dataclass
class ModbusConnectionInfo:
    host: str
    port: int
    slave_id: int


class ModbusClient:
    """Small async wrapper around pymodbus. Abstracted for easy mocking in tests."""

    def __init__(self, info: ModbusConnectionInfo) -> None:
        self._info = info
        self._client: AsyncModbusTcpClient | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        async with self._lock:
            if self._client is not None:
                return
            self._client = AsyncModbusTcpClient(self._info.host, port=self._info.port)
            connected = await self._client.connect()
            if connected is False:
                self._client = None
                raise RuntimeError(
                    f"Unable to connect to Modbus server {self._info.host}:{self._info.port}"
                )

    async def close(self) -> None:
        async with self._lock:
            if self._client is not None:
                maybe_awaitable = self._client.close()
                if isawaitable(maybe_awaitable):
                    await maybe_awaitable
                self._client = None

    async def read_holding(self, address: int, count: int = 1) -> list[int]:
        await self.connect()
        assert self._client is not None
        async with self._lock:
            rr = await self._client.read_holding_registers(address=address, count=count, slave=self._info.slave_id)
        if rr.isError():
            raise RuntimeError(f"Modbus read error at {address} count {count}: {rr}")
        return list(rr.registers)

    async def write_register(self, address: int, value: int) -> None:
        await self.connect()
        assert self._client is not None
        async with self._lock:
            wr = await self._client.write_register(address=address, value=value, slave=self._info.slave_id)
        if wr.isError():
            raise RuntimeError(f"Modbus write error at {address} value {value}: {wr}")
