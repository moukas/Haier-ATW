from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path
from typing import Any

from custom_components.haier_atw_ew11.const import (
    DEFAULT_RTU_OVER_TCP_PORT,
    DEFAULT_TIMEOUT,
    REGISTER_BASE,
    TRANSPORT_MODBUS_TCP,
    TRANSPORT_RTU_OVER_TCP,
)
from custom_components.haier_atw_ew11.modbus_client import ModbusClient, ModbusConnectionInfo


def _load_points() -> list[dict[str, Any]]:
    points_path = Path(__file__).resolve().parents[1] / "custom_components" / "haier_atw_ew11" / "points.json"
    with points_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_enum_pairs(desc: str) -> dict[int, str]:
    pattern = r"(\d+)\s*-\s*(.*?)(?=(?:,\s*\d+\s*-)|(?:\s+\d+\s*-)|$)"
    pairs = re.findall(pattern, desc or "")
    parsed: dict[int, str] = {}
    for value_s, label in pairs:
        cleaned = " ".join(str(label).split()).strip(" ,;")
        if cleaned:
            parsed[int(value_s)] = cleaned
    return parsed


def _decode_value(raw: int, scale: float, dtype: str) -> float | int:
    value = int(raw)
    if dtype == "int16" and value >= 0x8000:
        value = value - 0x10000
    decoded = value * scale
    if float(decoded).is_integer():
        return int(decoded)
    return round(float(decoded), 3)


def _build_ranges(addresses: list[int], max_chunk: int) -> list[tuple[int, int]]:
    if not addresses:
        return []
    ranges: list[tuple[int, int]] = []
    start = prev = addresses[0]
    for addr in addresses[1:]:
        if addr == prev + 1 and (addr - start + 1) <= max_chunk:
            prev = addr
            continue
        ranges.append((start, prev))
        start = prev = addr
    ranges.append((start, prev))
    return ranges


def _safe_print(text: str) -> None:
    print(text.encode("ascii", "backslashreplace").decode("ascii"))


async def _run(args: argparse.Namespace) -> int:
    points = _load_points()
    point_by_register = {int(p["register"]): p for p in points}

    registers: set[int] = set()
    if args.points_only:
        registers.update(
            int(p["register"]) for p in points if "R" in str(p.get("rw") or "")
        )
    if args.register:
        registers.update(int(r) for r in args.register)
    if args.range_start is not None and args.range_end is not None:
        start = min(args.range_start, args.range_end)
        end = max(args.range_start, args.range_end)
        registers.update(range(start, end + 1))

    if not registers:
        print("No registers selected. Use --points-only and/or --register and/or --range-start/--range-end.")
        return 2

    selected = sorted(r for r in registers if r >= REGISTER_BASE)
    addresses = sorted(r - REGISTER_BASE for r in selected)
    ranges = _build_ranges(addresses, max_chunk=max(int(args.max_chunk), 1))

    info = ModbusConnectionInfo(
        host=args.host,
        port=int(args.port),
        slave_id=int(args.slave_id),
        transport=str(args.transport),
        timeout=float(args.timeout),
        throttle_ms=int(args.throttle_ms),
        retries=int(args.retries),
    )
    client = ModbusClient(info)

    raw_by_register: dict[int, int] = {}
    try:
        await client.connect()
        for start_addr, end_addr in ranges:
            count = end_addr - start_addr + 1
            values = await client.read_holding(start_addr, count=count)
            for i, value in enumerate(values):
                register = REGISTER_BASE + start_addr + i
                raw_by_register[register] = int(value)
    finally:
        await client.close()

    results: list[dict[str, Any]] = []
    for register in selected:
        raw = raw_by_register.get(register)
        point = point_by_register.get(register, {})
        description = str(point.get("description", ""))
        enum_map = _parse_enum_pairs(description)
        scale = float(point.get("scale_read", point.get("scale", 1.0)))
        dtype = str(point.get("dtype", "uint16"))

        item: dict[str, Any] = {
            "register": register,
            "raw": raw,
            "decoded": None,
            "label": None,
            "function": point.get("function"),
            "rw": point.get("rw"),
            "unit": point.get("unit"),
            "description": description,
            "dtype": dtype,
            "scale": scale,
        }
        if raw is not None:
            item["decoded"] = _decode_value(raw, scale=scale, dtype=dtype)
            if enum_map:
                item["label"] = enum_map.get(int(raw))
        results.append(item)

    output = {
        "host": args.host,
        "port": int(args.port),
        "transport": args.transport,
        "slave_id": int(args.slave_id),
        "count": len(results),
        "results": results,
    }

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(output, ensure_ascii=True, indent=2), encoding="utf-8")
        _safe_print(f"Wrote JSON report: {out_path}")

    _safe_print(
        f"Read {len(results)} registers from {args.host}:{args.port} ({args.transport}, slave {args.slave_id})"
    )
    for item in results:
        suffix = f" {item['unit']}" if item.get("unit") else ""
        label = f" [{item['label']}]" if item.get("label") else ""
        _safe_print(
            f"{item['register']}: raw={item['raw']} decoded={item['decoded']}{suffix}{label} "
            f"- {item.get('function') or 'unknown'}"
        )

    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read Haier ATW EW11 Modbus holding registers in read-only mode."
    )
    parser.add_argument("--host", required=True, help="EW11 IP address or hostname.")
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_RTU_OVER_TCP_PORT,
        help="TCP port (typical: 8899 for rtu_over_tcp, 502 for modbus_tcp).",
    )
    parser.add_argument(
        "--transport",
        choices=[TRANSPORT_MODBUS_TCP, TRANSPORT_RTU_OVER_TCP],
        default=TRANSPORT_RTU_OVER_TCP,
        help="Transport type.",
    )
    parser.add_argument("--slave-id", type=int, default=1, help="Modbus slave ID.")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="Request timeout in seconds.")
    parser.add_argument("--retries", type=int, default=2, help="Retries per request.")
    parser.add_argument("--throttle-ms", type=int, default=60, help="Delay between requests in milliseconds.")
    parser.add_argument(
        "--points-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include readable registers from points.json (default: true).",
    )
    parser.add_argument(
        "--register",
        type=int,
        action="append",
        help="Add specific register(s) to read (can be repeated).",
    )
    parser.add_argument("--range-start", type=int, help="Range start register (inclusive).")
    parser.add_argument("--range-end", type=int, help="Range end register (inclusive).")
    parser.add_argument("--max-chunk", type=int, default=24, help="Maximum registers per Modbus read request.")
    parser.add_argument("--json-out", help="Optional JSON output path.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        return asyncio.run(_run(args))
    except Exception as err:  # noqa: BLE001
        _safe_print(f"Read failed: {type(err).__name__}: {err!r}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
