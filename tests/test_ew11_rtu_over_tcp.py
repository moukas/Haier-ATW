from __future__ import annotations

import asyncio

import pytest

from custom_components.haier_atw_ew11.const import TRANSPORT_RTU_OVER_TCP
from custom_components.haier_atw_ew11.modbus_client import (
    ModbusClient,
    ModbusConnectionInfo,
    append_crc,
    crc16_modbus,
    extract_rtu_frame,
)


def test_crc16_modbus_known_vector() -> None:
    payload = bytes((0x01, 0x03, 0x00, 0x00, 0x00, 0x0A))
    crc = crc16_modbus(payload)
    assert crc == 0xCDC5
    assert append_crc(payload)[-2:] == bytes((0xC5, 0xCD))


def test_extract_rtu_frame_handles_noise_and_keeps_tail() -> None:
    response = append_crc(bytes((0x01, 0x03, 0x04, 0x00, 0x2A, 0x00, 0x2B)))
    buffer = bytearray(b"\x99" + response + b"\xAA")

    frame = extract_rtu_frame(buffer, slave_id=1, expected_function=0x03)
    assert frame == response
    assert buffer == bytearray(b"\xAA")


@pytest.mark.asyncio
async def test_ew11_rtu_over_tcp_reads_and_writes_against_fake_server() -> None:
    async def _handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        data = bytearray()
        try:
            while True:
                chunk = await reader.read(256)
                if not chunk:
                    break
                data.extend(chunk)
                while len(data) >= 8:
                    if data[0] != 0x01:
                        del data[0]
                        continue
                    request = bytes(data[:8])
                    if crc16_modbus(request[:-2]) != int.from_bytes(request[-2:], byteorder="little"):
                        del data[0]
                        continue
                    del data[:8]

                    function = request[1]
                    if function == 0x03:
                        address = int.from_bytes(request[2:4], byteorder="big")
                        count = int.from_bytes(request[4:6], byteorder="big")
                        values = [address + 100 + i for i in range(count)]
                        payload = bytes((0x01, 0x03, count * 2)) + b"".join(
                            v.to_bytes(2, byteorder="big") for v in values
                        )
                        writer.write(append_crc(payload))
                        await writer.drain()
                    elif function == 0x06:
                        writer.write(request)
                        await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(_handler, host="127.0.0.1", port=0)
    host, port = server.sockets[0].getsockname()[:2]

    client = ModbusClient(
        ModbusConnectionInfo(
            host=host,
            port=port,
            slave_id=1,
            transport=TRANSPORT_RTU_OVER_TCP,
            timeout=1.0,
            throttle_ms=0,
            retries=0,
        )
    )
    try:
        values = await client.read_holding(0, 2)
        assert values == [100, 101]
        await client.write_register(5, 123)
    finally:
        await client.close()
        server.close()
        await server.wait_closed()
