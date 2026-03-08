from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_PROFILE,
    CONF_RETRIES,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    CONF_THROTTLE_MS,
    CONF_TIMEOUT,
    CONF_TRANSPORT,
    DEFAULT_RETRIES,
    TRANSPORT_LEGACY_EW11_RTU_OVER_TCP,
    TRANSPORT_RTU_OVER_TCP,
    DEFAULT_THROTTLE_MS,
    DEFAULT_TIMEOUT,
    DOMAIN,
    DEFAULT_PROFILE,
    TRANSPORT_MODBUS_TCP,
)
from .modbus_client import ModbusClient, ModbusConnectionInfo
from .profiles import load_profile

MAX_READ_REGISTERS_PER_REQUEST = 24
MODBUS_TCP_ABSOLUTE_ADDRESS_PORT = 8899


def _infer_scale_dtype(desc: str) -> tuple[float, str]:
    """Best-effort heuristic based on vendor text."""
    d = desc.lower()

    # Temperature-like (docs may use both normal and mojibake forms of Celsius).
    is_temperature = any(token in d for token in ("°c", "℃", "â„ƒ", "Â°c".lower()))
    if is_temperature:
        if re.search(r"unit[:\s]*0\.1", d):
            return 0.1, "int16"
        if re.search(r"unit[:\s]*0\.5", d):
            return 0.5, "int16"
        if re.search(r"unit[:\s]*1(\D|$)", d):
            return 1.0, "int16"

    if "unit 0.01" in d:
        return 0.01, "uint16"
    if "unit 0.1 hz" in d:
        return 0.1, "uint16"
    if "unit 0.1 a" in d:
        return 0.1, "uint16"
    if "unit 0.1 kw" in d:
        return 0.1, "uint16"
    # default raw
    return 1.0, "uint16"


def _build_contiguous_ranges(addresses: list[int]) -> list[tuple[int, int]]:
    if not addresses:
        return []
    ranges: list[tuple[int, int]] = []
    start = prev = addresses[0]
    for addr in addresses[1:]:
        if addr == prev + 1:
            prev = addr
            continue
        ranges.append((start, prev))
        start = prev = addr
    ranges.append((start, prev))
    return ranges


def _split_range(start: int, end: int, chunk_size: int) -> list[tuple[int, int]]:
    chunk = max(int(chunk_size), 1)
    out: list[tuple[int, int]] = []
    cursor = start
    while cursor <= end:
        chunk_end = min(cursor + chunk - 1, end)
        out.append((cursor, chunk_end))
        cursor = chunk_end + 1
    return out


def _use_absolute_addressing(
    transport: str,
    port: int,
    absolute_addressing_ports: set[int] | None = None,
) -> bool:
    """Return whether the active profile/transport expects absolute register addressing."""
    ports = absolute_addressing_ports
    if ports is None:
        ports = {MODBUS_TCP_ABSOLUTE_ADDRESS_PORT}
    return transport == TRANSPORT_MODBUS_TCP and int(port) in ports


class HaierAtwCoordinator(DataUpdateCoordinator[dict[int, int]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.profile = load_profile(entry.data.get(CONF_PROFILE, DEFAULT_PROFILE))
        self.profile_id = str(self.profile["id"])
        self.special = dict(self.profile.get("special", {}))
        self.mode_options = dict(self.profile.get("mode_options", {}))
        self.mode_to_hvac = dict(self.profile.get("mode_to_hvac", {}))
        self.hvac_to_mode = dict(self.profile.get("hvac_to_mode", {}))
        self.current_temperature_register = int(self.profile.get("current_temperature_register", 40142))
        self._fault_registers = set(self.profile.get("fault_registers", set()))
        self._register_base = int(self.profile.get("register_base", 40001))

        info = ModbusConnectionInfo(
            host=entry.data[CONF_HOST],
            port=entry.data[CONF_PORT],
            slave_id=entry.data[CONF_SLAVE_ID],
            transport=(
                TRANSPORT_RTU_OVER_TCP
                if entry.data.get(CONF_TRANSPORT) == TRANSPORT_LEGACY_EW11_RTU_OVER_TCP
                else entry.data.get(CONF_TRANSPORT, TRANSPORT_MODBUS_TCP)
            ),
            timeout=float(entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)),
            throttle_ms=int(entry.data.get(CONF_THROTTLE_MS, DEFAULT_THROTTLE_MS)),
            retries=int(entry.data.get(CONF_RETRIES, DEFAULT_RETRIES)),
        )
        self.client = ModbusClient(info)
        self._use_absolute_addressing = _use_absolute_addressing(
            transport=info.transport,
            port=info.port,
            absolute_addressing_ports=set(self.profile.get("absolute_addressing_ports", set())),
        )
        self.points = list(self.profile["points"])

        scan = int(entry.data.get(CONF_SCAN_INTERVAL, 10))
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=scan),
        )

    async def async_close(self) -> None:
        await self.client.close()

    def get_point_by_register(self, register: int) -> dict[str, Any] | None:
        for p in self.points:
            if p.get("register") == register:
                return p
        return None

    def get_raw_by_register(self, register: int) -> int | None:
        if self.data is None:
            return None
        return self.data.get(register)

    def register_to_address(self, register: int) -> int:
        if self._use_absolute_addressing:
            return int(register)
        return int(register) - self._register_base

    def address_to_register(self, address: int) -> int:
        if self._use_absolute_addressing:
            return int(address)
        return int(address) + self._register_base

    def get_special(self, key: str) -> dict[str, Any] | None:
        return self.special.get(key)

    def is_fault_register(self, register: int) -> bool:
        return int(register) in self._fault_registers

    async def _async_update_data(self) -> dict[int, int]:
        try:
            # Read all readable points. Group contiguous addresses for fewer requests.
            read_addrs = sorted(
                {
                    self.register_to_address(int(p["register"]))
                    for p in self.points
                    if "R" in (p.get("rw") or "")
                }
            )
            data: dict[int, int] = {}
            if not read_addrs:
                return data

            # Build contiguous ranges and split them into smaller chunks.
            # EW11 links are often more stable with shorter read requests.
            ranges = _build_contiguous_ranges(read_addrs)
            for s, e in ranges:
                for chunk_start, chunk_end in _split_range(
                    s, e, chunk_size=MAX_READ_REGISTERS_PER_REQUEST
                ):
                    count = chunk_end - chunk_start + 1
                    regs = await self.client.read_holding(address=chunk_start, count=count)
                    for i, val in enumerate(regs):
                        register = self.address_to_register(chunk_start + i)
                        data[register] = int(val)

            return data
        except Exception as err:
            raise UpdateFailed(str(err)) from err

    def infer_meta(self, register: int) -> tuple[float, str]:
        """Return (scale, dtype) for a register.
        Prefer explicit metadata from points.json; fall back to heuristic parser.
        """
        p = self.get_point_by_register(register)
        if not p:
            return 1.0, "uint16"
        if "scale" in p or "dtype" in p:
            return float(p.get("scale", 1.0)), str(p.get("dtype", "uint16"))
        return _infer_scale_dtype(p.get("description", ""))
