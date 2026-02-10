from __future__ import annotations

import argparse
import asyncio
import logging
from collections.abc import Iterable


LOGGER = logging.getLogger("mock_ew11_haier")


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


class HaierRegisterModel:
    """0-based holding register model for Haier ATW-like behavior."""

    def __init__(self) -> None:
        self._regs: dict[int, int] = {}
        self._init_defaults()

    def _init_defaults(self) -> None:
        # Writable control registers 40001-40010 -> addresses 0-9
        self._regs[0] = 0    # power command
        self._regs[1] = 2    # mode command (Heat)
        self._regs[2] = 32   # zone1 setpoint (16.0C in 0.5 units)
        self._regs[3] = 32   # zone2 setpoint
        self._regs[4] = 96   # dhw setpoint (48.0C in 0.5 units)
        self._regs[5] = 56   # pool setpoint (28.0C in 0.5 units)
        self._regs[6] = 60   # sterilization setpoint
        self._regs[8] = 0    # eco command
        self._regs[9] = 0    # fast dhw command

        # Verification / status mirrors around 401xx
        self._regs[100] = self._regs[0]   # 40101 power status
        self._regs[101] = self._regs[1]   # 40102 mode status
        self._regs[102] = self._regs[2]   # 40103 zone1
        self._regs[103] = self._regs[3]   # 40104 zone2
        self._regs[104] = self._regs[4]   # 40105 dhw
        self._regs[105] = self._regs[5]   # 40106 pool
        self._regs[106] = self._regs[6]   # 40107 sterilization
        self._regs[109] = self._regs[8]   # 40110 eco status
        self._regs[110] = self._regs[9]   # 40111 fast dhw status

        # A few telemetry registers often used in dashboards.
        self._regs[140] = 120  # 40141 outdoor temp 12.0C (0.1 unit)
        self._regs[141] = 330  # 40142 water outlet temp 33.0C
        self._regs[203] = 0    # 40204 fault subcode
        self._regs[204] = 0    # 40205 fault code

    def read(self, start: int, count: int) -> list[int]:
        return [int(self._regs.get(addr, 0)) & 0xFFFF for addr in range(start, start + count)]

    def write_single(self, address: int, value: int) -> None:
        self._regs[address] = int(value) & 0xFFFF
        self._apply_side_effects([address])

    def write_many(self, start: int, values: Iterable[int]) -> None:
        changed: list[int] = []
        for i, value in enumerate(values):
            addr = start + i
            self._regs[addr] = int(value) & 0xFFFF
            changed.append(addr)
        self._apply_side_effects(changed)

    def _apply_side_effects(self, changed: Iterable[int]) -> None:
        for addr in changed:
            if addr == 0:
                self._regs[100] = self._regs[0]
            elif addr == 1:
                self._regs[101] = self._regs[1]
            elif addr == 2:
                self._regs[102] = self._regs[2]
            elif addr == 3:
                self._regs[103] = self._regs[3]
            elif addr == 4:
                self._regs[104] = self._regs[4]
            elif addr == 5:
                self._regs[105] = self._regs[5]
            elif addr == 6:
                self._regs[106] = self._regs[6]
            elif addr == 8:
                self._regs[109] = self._regs[8]
            elif addr == 9:
                self._regs[110] = self._regs[9]


class Ew11RtuTcpMockServer:
    def __init__(self, host: str, port: int, slave_id: int) -> None:
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._model = HaierRegisterModel()
        self._server: asyncio.AbstractServer | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle_client, self._host, self._port)
        sockets = self._server.sockets or []
        bind = sockets[0].getsockname() if sockets else (self._host, self._port)
        LOGGER.info("EW11 mock server listening on %s (slave_id=%s)", bind, self._slave_id)

    async def serve_forever(self) -> None:
        if self._server is None:
            raise RuntimeError("Server not started")
        async with self._server:
            await self._server.serve_forever()

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        LOGGER.info("Client connected: %s", peer)
        buffer = bytearray()
        try:
            while True:
                chunk = await reader.read(1024)
                if not chunk:
                    break
                buffer.extend(chunk)

                while True:
                    frame = self._extract_request_frame(buffer)
                    if frame is None:
                        break
                    response = self._handle_request(frame)
                    if response is not None:
                        writer.write(response)
                        await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()
            LOGGER.info("Client disconnected: %s", peer)

    def _extract_request_frame(self, buffer: bytearray) -> bytes | None:
        while len(buffer) >= 8:
            if buffer[0] != self._slave_id:
                del buffer[0]
                continue

            func = buffer[1]
            if func in (0x03, 0x06):
                frame_len = 8
            elif func == 0x10:
                if len(buffer) < 7:
                    return None
                byte_count = buffer[6]
                frame_len = 9 + byte_count
            else:
                # Unknown function: still consume 8 bytes if possible to avoid deadlock.
                frame_len = 8

            if len(buffer) < frame_len:
                return None

            frame = bytes(buffer[:frame_len])
            del buffer[:frame_len]

            expected_crc = int.from_bytes(frame[-2:], byteorder="little")
            if crc16_modbus(frame[:-2]) != expected_crc:
                LOGGER.warning("Bad CRC in request, dropping frame: %s", frame.hex(" "))
                continue
            return frame
        return None

    def _exception(self, function: int, code: int) -> bytes:
        return append_crc(bytes((self._slave_id, function | 0x80, code)))

    def _handle_request(self, frame: bytes) -> bytes | None:
        func = frame[1]

        if func == 0x03:
            start = int.from_bytes(frame[2:4], byteorder="big")
            count = int.from_bytes(frame[4:6], byteorder="big")
            if count < 1 or count > 125:
                return self._exception(func, 0x03)
            if start < 0 or start + count > 10000:
                return self._exception(func, 0x02)
            regs = self._model.read(start, count)
            payload = bytes((self._slave_id, 0x03, count * 2)) + b"".join(
                reg.to_bytes(2, byteorder="big") for reg in regs
            )
            LOGGER.debug("Read 0x03 start=%d count=%d -> %s", start, count, regs)
            return append_crc(payload)

        if func == 0x06:
            address = int.from_bytes(frame[2:4], byteorder="big")
            value = int.from_bytes(frame[4:6], byteorder="big")
            if address < 0 or address >= 10000:
                return self._exception(func, 0x02)
            self._model.write_single(address, value)
            LOGGER.debug("Write 0x06 addr=%d value=%d", address, value)
            # Standard response is echo.
            return frame

        if func == 0x10:
            start = int.from_bytes(frame[2:4], byteorder="big")
            qty = int.from_bytes(frame[4:6], byteorder="big")
            byte_count = frame[6]
            values_bytes = frame[7:-2]
            if qty < 1 or qty > 123:
                return self._exception(func, 0x03)
            if byte_count != qty * 2 or len(values_bytes) != byte_count:
                return self._exception(func, 0x03)
            if start < 0 or start + qty > 10000:
                return self._exception(func, 0x02)

            values = [
                int.from_bytes(values_bytes[i : i + 2], byteorder="big")
                for i in range(0, byte_count, 2)
            ]
            self._model.write_many(start, values)
            LOGGER.debug("Write 0x10 start=%d qty=%d values=%s", start, qty, values)
            payload = bytes(
                (
                    self._slave_id,
                    0x10,
                    (start >> 8) & 0xFF,
                    start & 0xFF,
                    (qty >> 8) & 0xFF,
                    qty & 0xFF,
                )
            )
            return append_crc(payload)

        return self._exception(func, 0x01)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mock EW11 transparent TCP<->UART server with Haier-like Modbus RTU responses."
    )
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8899, help="Bind port (default: 8899)")
    parser.add_argument("--slave-id", type=int, default=1, help="Modbus slave id (default: 1)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


async def _amain() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    server = Ew11RtuTcpMockServer(host=args.host, port=args.port, slave_id=args.slave_id)
    await server.start()
    await server.serve_forever()


def main() -> None:
    try:
        asyncio.run(_amain())
    except KeyboardInterrupt:
        LOGGER.info("Server stopped")


if __name__ == "__main__":
    main()
