# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [0.2.0] - 2026-03-08
### Added
- Heat pump profile support (`profile`) with per-model register maps.
- File-based profile definitions in `custom_components/haier_atw_ew11/profiles/*.profile.json`.
- New built-in compact profile `haier_compact_auxxfychra`.
- Config flow heat pump type selector as a dropdown list.
- Device info now includes connected host/IP in the displayed device name.
- Device info now exposes `configuration_url` built from configured host/port.
- Local integration brand assets in `custom_components/haier_atw_ew11/brand/`.
- Regression tests for Modbus value interpretation and profile behavior.

### Changed
- Existing EW11 mapping moved to profile definition while keeping backward compatibility.
- Profile options in config flow show only heat pump type names.
- Profile loading is dynamic from profile files to simplify future extensions.

### Fixed
- Fault register attributes are now profile-aware.

## [0.1.0] - 2026-03-01
### Added
- Initial release with EW11 Modbus support, core entities, and basic tests.
