# Haier ATW (EW11 Modbus)

Custom Home Assistant integration (HACS) for Haier ATW heat pumps connected via Elfin EW11 (Modbus TCP gateway).

## Features
- Modbus TCP via EW11
- Switches: Power, ECO, Fast DHW
- Select: Mode
- Numbers: ZONE1/ZONE2/DHW/Pool/Sterilization setpoints
- Sensors: auto-generated from the included `points.json` point table

## Install (HACS)
1. Add this repository as a custom repository (Integration).
2. Install and restart Home Assistant.
3. Add integration: **Settings → Devices & Services → Add Integration → Haier ATW (EW11 Modbus)**

## Notes
- Uses 0-based addressing internally (40001 -> address 0).
- Point table extracted from vendor document.


## Lovelace (dashboard)
Hotová karta je v `examples/lovelace_card.yaml` – zkopíruj do UI (Raw YAML editor).

## Fault code / subcode
Senzory `Current fault code` (40205) a `Current fault subcode` (40204) mají atributy `raw` a `hex` pro snadné ladění.

## Dev setup (Python 3.12)
1. Run: `powershell -ExecutionPolicy Bypass -File .\scripts\setup_dev.ps1 -RunTests`
2. The script creates `.venv312`, installs `requirements-dev.txt`, and runs `pytest`.
