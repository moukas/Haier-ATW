from __future__ import annotations

import json
import os
import re
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_SLAVE_ID,
    CONF_SCAN_INTERVAL,
)
from .modbus_client import ModbusClient, ModbusConnectionInfo


def _load_points() -> list[dict[str, Any]]:
    here = os.path.dirname(__file__)
    with open(os.path.join(here, "points.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def _infer_scale_dtype(desc: str) -> tuple[float, str]:
    """Best-effort heuristic based on vendor text."""
    d = desc.lower()
    # temperature-like
    m = re.search(r"unit\s*0\.1", d)
    if "℃" in desc or "°c" in d or "c" in d and "unit" in d:
        if m:
            return 0.1, "int16"
        m2 = re.search(r"unit\s*1\s*℃", d)
        if m2:
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


class HaierAtwCoordinator(DataUpdateCoordinator[dict[int, int]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        info = ModbusConnectionInfo(
            host=entry.data[CONF_HOST],
            port=entry.data[CONF_PORT],
            slave_id=entry.data[CONF_SLAVE_ID],
        )
        self.client = ModbusClient(info)
        self.points = _load_points()

        scan = int(entry.data.get(CONF_SCAN_INTERVAL, 10))
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
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
        addr = register - 40001
        return self.data.get(addr)

    async def _async_update_data(self) -> dict[int, int]:
        try:
            # Read all readable points. Group contiguous addresses for fewer requests.
            read_addrs = sorted({p["ha_address"] for p in self.points if "R" in (p.get("rw") or "")})
            data: dict[int, int] = {}
            if not read_addrs:
                return data

            # Build contiguous ranges
            ranges = []
            start = prev = read_addrs[0]
            for a in read_addrs[1:]:
                if a == prev + 1:
                    prev = a
                    continue
                ranges.append((start, prev))
                start = prev = a
            ranges.append((start, prev))

            for (s, e) in ranges:
                count = e - s + 1
                regs = await self.client.read_holding(address=s, count=count)
                for i, val in enumerate(regs):
                    data[s + i] = int(val)

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
