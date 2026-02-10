# Haier ATW (EW11 Modbus)

![Project icon](assets/haier_atw_ew11_icon.svg)

Custom Home Assistant integration (HACS) for Haier ATW heat pumps connected via Elfin EW11.

## Features
- Transport selection: `modbus_tcp` or `rtu_over_tcp`
- Switches: Power, ECO, Fast DHW
- Select: Mode
- Numbers: ZONE1/ZONE2/DHW/Pool/Sterilization setpoints
- Sensors: auto-generated from the included `points.json` point table
- Request serialization for RS-485 single-master bus (`asyncio.Lock`)
- Configurable timeout, retries, and throttle between requests

## Install (HACS)
1. Add this repository as a custom repository (Integration).
2. Install and restart Home Assistant.
3. Add integration: Settings -> Devices & Services -> Add Integration -> Haier ATW (EW11 Modbus).

## EW11 transparent tunnel mode (`rtu_over_tcp`)
Set EW11 to:
- Network mode: TCP Server
- Route/Work mode: UART (transparent stream)
- Serial line: 9600 8N1
- RS-485: half-duplex

In this mode EW11 is not a Modbus/TCP gateway. The integration sends and parses Modbus RTU ADU frames directly (including CRC16, poly `0xA001`, little-endian).

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

## Notes
- Uses strict 0-based addressing internally: `address = register - 40001`.
- Existing Haier register mapping is kept (e.g., `40001`, `401xx`).
- Point table extracted from vendor document.
- Read sensors expose decoded value labels in attributes, including Czech variants (`value_label_cs`, `value_options_cs`) when enum-like values are available.

## Lovelace (dashboard)
Ready card is in `examples/lovelace_card.yaml`.

## Fault code / subcode
Sensors `Current fault code` (40205) and `Current fault subcode` (40204) expose attributes `raw` and `hex` for easier diagnostics.

## Dev setup (Python 3.12)
1. Run: `powershell -ExecutionPolicy Bypass -File .\scripts\setup_dev.ps1 -RunTests`
2. The script creates `.venv312`, installs `requirements-dev.txt`, and runs `pytest`.
