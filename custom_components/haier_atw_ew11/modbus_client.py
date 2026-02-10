from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from inspect import isawaitable

from pymodbus.client import AsyncModbusTcpClient

from .const import (
    DEFAULT_RETRIES,
    DEFAULT_THROTTLE_MS,
    DEFAULT_TIMEOUT,
    TRANSPORT_LEGACY_EW11_RTU_OVER_TCP,
    TRANSPORT_MODBUS_TCP,
    TRANSPORT_RTU_OVER_TCP,
)


def crc16_modbus(payload: bytes) -> int:
    crc = 0xFFFF
    for byte in payload:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def append_crc(payload: bytes) -> bytes:
    crc = crc16_modbus(payload)
    return payload + bytes((crc & 0xFF, (crc >> 8) & 0xFF))


def extract_rtu_frame(buffer: bytearray, slave_id: int, expected_function: int) -> bytes | None:
    while len(buffer) >= 5:
        if buffer[0] != slave_id:
            del buffer[0]
            continue

        function = buffer[1]
        if function == (expected_function | 0x80):
            expected_len = 5
        elif function == expected_function == 0x03:
            if len(buffer) < 3:
                return None
            expected_len = 3 + buffer[2] + 2
        elif function == expected_function and function in (0x06, 0x10):
            expected_len = 8
        else:
            del buffer[0]
            continue

        if len(buffer) < expected_len:
            return None

        frame = bytes(buffer[:expected_len])
        expected_crc = int.from_bytes(frame[-2:], byteorder="little")
        if crc16_modbus(frame[:-2]) != expected_crc:
            del buffer[0]
            continue

        del buffer[:expected_len]
        return frame
    return None


@dataclass
class ModbusConnectionInfo:
    host: str
    port: int
    slave_id: int
    transport: str = TRANSPORT_MODBUS_TCP
    timeout: float = DEFAULT_TIMEOUT
    throttle_ms: int = DEFAULT_THROTTLE_MS
    retries: int = DEFAULT_RETRIES


class ModbusClient:
    """Async wrapper supporting pymodbus TCP and EW11 RTU-over-TCP tunnel."""

    def __init__(self, info: ModbusConnectionInfo) -> None:
        self._info = info
        if info.transport in (TRANSPORT_RTU_OVER_TCP, TRANSPORT_LEGACY_EW11_RTU_OVER_TCP):
            self._transport: _BaseTransport = _Ew11RtuOverTcpTransport(info)
        else:
            self._transport = _ModbusTcpTransport(info)

    async def connect(self) -> None:
        await self._transport.connect()

    async def close(self) -> None:
        await self._transport.close()

    async def read_holding(self, address: int, count: int = 1) -> list[int]:
        return await self._transport.read_holding(address=address, count=count)

    async def write_register(self, address: int, value: int) -> None:
        await self._transport.write_register(address=address, value=value)


class _BaseTransport:
    def __init__(self, info: ModbusConnectionInfo) -> None:
        self._info = info
        self._request_lock = asyncio.Lock()
        self._connect_lock = asyncio.Lock()
        self._last_request_monotonic = 0.0

    async def connect(self) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError

    async def read_holding(self, address: int, count: int = 1) -> list[int]:
        raise NotImplementedError

    async def write_register(self, address: int, value: int) -> None:
        raise NotImplementedError

    async def _throttle_locked(self) -> None:
        throttle_s = max(float(self._info.throttle_ms), 0.0) / 1000.0
        if throttle_s <= 0:
            return
        elapsed = time.monotonic() - self._last_request_monotonic
        if elapsed < throttle_s:
            await asyncio.sleep(throttle_s - elapsed)

    def _mark_request_locked(self) -> None:
        self._last_request_monotonic = time.monotonic()


class _ModbusTcpTransport(_BaseTransport):
    def __init__(self, info: ModbusConnectionInfo) -> None:
        super().__init__(info)
        self._client: AsyncModbusTcpClient | None = None

    async def connect(self) -> None:
        async with self._connect_lock:
            if self._client is not None:
                return
            self._client = AsyncModbusTcpClient(
                self._info.host,
                port=self._info.port,
                timeout=float(self._info.timeout),
            )
            connected = await asyncio.wait_for(self._client.connect(), timeout=float(self._info.timeout))
            if connected is False:
                self._client = None
                raise RuntimeError(
                    f"Unable to connect to Modbus server {self._info.host}:{self._info.port}"
                )

    async def close(self) -> None:
        async with self._connect_lock:
            if self._client is None:
                return
            maybe_awaitable = self._client.close()
            if isawaitable(maybe_awaitable):
                await maybe_awaitable
            self._client = None

    async def read_holding(self, address: int, count: int = 1) -> list[int]:
        return await self._with_retries(self._read_holding_once, address, count)

    async def write_register(self, address: int, value: int) -> None:
        await self._with_retries(self._write_register_once, address, value)

    async def _with_retries(self, op, *args):  # noqa: ANN202, ANN001
        retries = max(int(self._info.retries), 0)
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                await self.connect()
                return await op(*args)
            except Exception as err:
                last_error = err
                await self.close()
                if attempt >= retries:
                    break
        assert last_error is not None
        raise last_error

    async def _read_holding_once(self, address: int, count: int) -> list[int]:
        assert self._client is not None
        async with self._request_lock:
            await self._throttle_locked()
            try:
                rr = await asyncio.wait_for(
                    self._client.read_holding_registers(
                        address=address,
                        count=count,
                        slave=self._info.slave_id,
                    ),
                    timeout=float(self._info.timeout),
                )
            finally:
                self._mark_request_locked()
        if rr.isError():
            raise RuntimeError(f"Modbus read error at {address} count {count}: {rr}")
        return list(rr.registers)

    async def _write_register_once(self, address: int, value: int) -> None:
        assert self._client is not None
        async with self._request_lock:
            await self._throttle_locked()
            try:
                wr = await asyncio.wait_for(
                    self._client.write_register(
                        address=address,
                        value=value,
                        slave=self._info.slave_id,
                    ),
                    timeout=float(self._info.timeout),
                )
            finally:
                self._mark_request_locked()
        if wr.isError():
            raise RuntimeError(f"Modbus write error at {address} value {value}: {wr}")


class _Ew11RtuOverTcpTransport(_BaseTransport):
    def __init__(self, info: ModbusConnectionInfo) -> None:
        super().__init__(info)
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._buffer = bytearray()

    async def connect(self) -> None:
        async with self._connect_lock:
            if self._reader is not None and self._writer is not None:
                return
            connect_coro = asyncio.open_connection(self._info.host, self._info.port)
            self._reader, self._writer = await asyncio.wait_for(
                connect_coro, timeout=float(self._info.timeout)
            )
            self._buffer.clear()

    async def close(self) -> None:
        async with self._connect_lock:
            if self._writer is None:
                self._reader = None
                return
            self._writer.close()
            await self._writer.wait_closed()
            self._writer = None
            self._reader = None
            self._buffer.clear()

    async def read_holding(self, address: int, count: int = 1) -> list[int]:
        payload = bytes(
            (
                self._info.slave_id,
                0x03,
                (address >> 8) & 0xFF,
                address & 0xFF,
                (count >> 8) & 0xFF,
                count & 0xFF,
            )
        )
        frame = await self._request_with_retries(append_crc(payload), expected_function=0x03)
        function = frame[1]
        if function & 0x80:
            raise RuntimeError(f"Modbus exception response for read at {address}: 0x{frame[2]:02X}")
        byte_count = frame[2]
        data = frame[3 : 3 + byte_count]
        if byte_count != count * 2:
            raise RuntimeError(
                f"Unexpected response length for read at {address}: got {byte_count} bytes"
            )
        return [int.from_bytes(data[i : i + 2], byteorder="big") for i in range(0, byte_count, 2)]

    async def write_register(self, address: int, value: int) -> None:
        payload = bytes(
            (
                self._info.slave_id,
                0x06,
                (address >> 8) & 0xFF,
                address & 0xFF,
                (value >> 8) & 0xFF,
                value & 0xFF,
            )
        )
        frame = await self._request_with_retries(append_crc(payload), expected_function=0x06)
        function = frame[1]
        if function & 0x80:
            raise RuntimeError(f"Modbus exception response for write at {address}: 0x{frame[2]:02X}")
        if frame[2:6] != payload[2:6]:
            raise RuntimeError("Unexpected echo response for write_register")

    async def _request_with_retries(self, request_adu: bytes, expected_function: int) -> bytes:
        retries = max(int(self._info.retries), 0)
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                return await self._request_once(request_adu, expected_function)
            except Exception as err:
                last_error = err
                await self.close()
                if attempt >= retries:
                    break
        assert last_error is not None
        raise last_error

    async def _request_once(self, request_adu: bytes, expected_function: int) -> bytes:
        await self.connect()
        assert self._reader is not None
        assert self._writer is not None
        async with self._request_lock:
            await self._throttle_locked()
            try:
                self._writer.write(request_adu)
                await asyncio.wait_for(self._writer.drain(), timeout=float(self._info.timeout))
                return await self._read_response_frame(expected_function=expected_function)
            finally:
                self._mark_request_locked()

    async def _read_response_frame(self, expected_function: int) -> bytes:
        assert self._reader is not None
        while True:
            frame = extract_rtu_frame(self._buffer, self._info.slave_id, expected_function)
            if frame is not None:
                return frame
            chunk = await asyncio.wait_for(self._reader.read(256), timeout=float(self._info.timeout))
            if not chunk:
                raise RuntimeError("EW11 closed TCP stream before full Modbus RTU response")
            self._buffer.extend(chunk)
