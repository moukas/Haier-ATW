from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_NAME,
    CONF_HOST,
    CONF_PORT,
    CONF_RETRIES,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    CONF_THROTTLE_MS,
    CONF_TIMEOUT,
    CONF_TRANSPORT,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_RETRIES,
    TRANSPORT_LEGACY_EW11_RTU_OVER_TCP,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE_ID,
    DEFAULT_THROTTLE_MS,
    DEFAULT_TIMEOUT,
    DOMAIN,
    TRANSPORT_MODBUS_TCP,
    TRANSPORTS,
)
from .coordinator import HaierAtwCoordinator

PLATFORMS: list[str] = ["sensor", "switch", "number", "select", "climate"]


_YAML_ENTRY_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_TRANSPORT, default=TRANSPORT_MODBUS_TCP): vol.In(
            TRANSPORTS + [TRANSPORT_LEGACY_EW11_RTU_OVER_TCP]
        ),
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.positive_int,
        vol.Optional(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): cv.positive_int,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.positive_int,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.All(vol.Coerce(float), vol.Range(min=0.001)),
        vol.Optional(CONF_THROTTLE_MS, default=DEFAULT_THROTTLE_MS): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional(CONF_RETRIES, default=DEFAULT_RETRIES): vol.All(vol.Coerce(int), vol.Range(min=0)),
    }
)
CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.All(cv.ensure_list, [_YAML_ENTRY_SCHEMA])}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    entries = config.get(DOMAIN, [])
    for entry_conf in entries:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_IMPORT},
                data=dict(entry_conf),
            )
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = HaierAtwCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if coordinator is not None:
            await coordinator.async_close()
    return unload_ok
