# Haier ATW (EW11 Modbus)

![Project icon](assets/haier_atw_ew11_icon.svg)

Custom Home Assistant integration (HACS) for Haier ATW heat pumps connected over RS-485 Modbus via EW11/TCP bridges.

## Compatibility
- Heat pump family: Haier ATW units exposing the vendor Modbus register map included in `custom_components/haier_atw_ew11/points.json`.
- Physical board connector: `CN3` (`Modbus A3`, `Modbus B3`) on the indoor/control board.
- Home Assistant: see `hacs.json` / `manifest.json` minimum versions.

## Supported TCP -> Modbus devices
This integration supports two transport modes:
- `modbus_tcp`: standard Modbus/TCP gateway mode.
- `rtu_over_tcp`: transparent TCP tunnel carrying raw Modbus RTU frames.

Known bridge compatibility:
- Elfin EW11: supported.
- Other TCP<->RS485 gateways: supported when they behave as either:
  - Modbus/TCP gateway (use `transport=modbus_tcp`), or
  - transparent serial tunnel (use `transport=rtu_over_tcp`).

Important addressing note:
- EW11 with `Protocol=Modbus` on port `8899` typically uses absolute register addressing (`40101`, `40102`, ...).
- Transparent RTU tunnel mode uses RTU framing and standard register offset handling.

## Wiring (RS-485)
- Heat pump board: `CN3`.
- Connect gateway `A` to `A3`, gateway `B` to `B3`.
- Keep one RS-485 master on the bus.
- Use twisted pair and keep polarity consistent end-to-end.

## Features
- Transport selection: `modbus_tcp` or `rtu_over_tcp`
- Switches: Power, ECO, Fast DHW
- Select: Mode
- Numbers: ZONE1/ZONE2/DHW/Pool/Sterilization setpoints
- Climate entity: `ZONE1 Climate` (for Home Assistant Climate dashboard/control panel)
- Sensors: auto-generated from the included `points.json` point table
- Request serialization for RS-485 single-master bus (`asyncio.Lock`)
- Configurable timeout, retries, and throttle between requests

## Install (HACS)
1. Add this repository as a custom repository (Integration).
2. Install and restart Home Assistant.
3. Add integration: Settings -> Devices & Services -> Add Integration -> Haier ATW (EW11 Modbus).

## EW11 setup: transparent tunnel (`rtu_over_tcp`)
Set EW11 to:
- Network mode: TCP Server
- Route/Work mode: UART (transparent stream)
- Serial line: 9600 8N1
- RS-485: half-duplex
- Protocol: transparent/serial tunnel (not Modbus gateway mode)

In this mode EW11 is not a Modbus/TCP gateway. The integration sends and parses Modbus RTU ADU frames directly (including CRC16, poly `0xA001`, little-endian).

## EW11 setup: Modbus gateway (`modbus_tcp`)
Set EW11 to:
- Network mode: TCP Server
- Protocol: Modbus
- Serial line: 9600 8N1
- RS-485: half-duplex
- Integration settings: `transport=modbus_tcp`, `port=8899`, `slave_id=1` (typical)

## YAML example
```yaml
haier_atw_ew11:
  - host: 192.168.1.50
    port: 8899
    transport: rtu_over_tcp
    slave_id: 1
    timeout: 3.0
    throttle_ms: 60
    retries: 2
    scan_interval: 10
```

## Mock EW11 server (for local testing)
Use the included EW11/Haier mock server:

```powershell
.\.venv312\Scripts\python.exe -B .\scripts\mock_ew11_haier_server.py --host 0.0.0.0 --port 8899 --slave-id 1 --debug
```

Then point integration host/port to this machine and `8899`.

## Read-only register scan (real EW11)
For safe diagnostics (no writes), run:

```powershell
$env:PYTHONPATH='.'
.\.venv312\Scripts\python.exe -B .\scripts\read_ew11_registers.py --host 192.168.2.154 --transport modbus_tcp --port 8899 --slave-id 1 --timeout 3 --retries 2 --json-out .\tmp\ew11_scan.json
```

Notes:
- Use `--transport rtu_over_tcp --port 8899` for transparent EW11 tunnel mode.
- Use `--register 40142 --register 40204` or `--range-start 40101 --range-end 40120` for targeted reads.
- Output JSON can be used to verify scaling/labels against `points.json` before changing entities.

## Notes
- Uses transport-specific address mapping internally.
- Existing Haier register mapping is kept (e.g., `40001`, `401xx`).
- Point table extracted from vendor document.
- Read sensors expose decoded value labels in attributes, including Czech variants (`value_label_cs`, `value_options_cs`) when enum-like values are available.
- For unstable EW11 links, start with: `transport=rtu_over_tcp`, `port=8899`, `timeout=4-5`, `retries=3`, `throttle_ms=120-200`, `scan_interval=15-30`.
- Coordinator reads are internally chunked into smaller requests to reduce timeout risk on noisy RS-485/EW11 paths.

## Lovelace (dashboard)
Ready card is in `examples/lovelace_card.yaml`.

## Fault code / subcode
Sensors `Current fault code` (40205) and `Current fault subcode` (40204) expose attributes `raw` and `hex` for easier diagnostics.

## Dev setup (Python 3.12)
1. Run: `powershell -ExecutionPolicy Bypass -File .\scripts\setup_dev.ps1 -RunTests`
2. The script creates `.venv312`, installs `requirements-dev.txt`, and runs `pytest`.
