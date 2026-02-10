from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_RETRIES,
    CONF_SLAVE_ID,
    CONF_SCAN_INTERVAL,
    CONF_THROTTLE_MS,
    CONF_TIMEOUT,
    CONF_TRANSPORT,
    DEFAULT_PORT,
    DEFAULT_RETRIES,
    DEFAULT_SLAVE_ID,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_THROTTLE_MS,
    DEFAULT_TIMEOUT,
    TRANSPORT_EW11_RTU_OVER_TCP,
    TRANSPORT_MODBUS_TCP,
    TRANSPORTS,
)

class HaierAtwConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    
    async def _validate_and_create_entry(self, user_input: dict[str, Any], source: str = "user") -> FlowResult:
        errors: dict[str, str] = {}

        host = str(user_input[CONF_HOST]).strip()
        transport = str(user_input.get(CONF_TRANSPORT, TRANSPORT_MODBUS_TCP))
        port = int(user_input.get(CONF_PORT, DEFAULT_PORT))
        slave_id = int(user_input.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID))
        scan_interval = int(user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        timeout = float(user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT))
        throttle_ms = int(user_input.get(CONF_THROTTLE_MS, DEFAULT_THROTTLE_MS))
        retries = int(user_input.get(CONF_RETRIES, DEFAULT_RETRIES))

        if not host:
            errors[CONF_HOST] = "required"
        elif transport not in TRANSPORTS:
            errors[CONF_TRANSPORT] = "invalid_transport"
        elif port <= 0:
            errors[CONF_PORT] = "invalid_port"
        elif slave_id <= 0:
            errors[CONF_SLAVE_ID] = "invalid_slave_id"
        elif scan_interval <= 0:
            errors[CONF_SCAN_INTERVAL] = "invalid_scan_interval"
        elif timeout <= 0:
            errors[CONF_TIMEOUT] = "invalid_timeout"
        elif throttle_ms < 0:
            errors[CONF_THROTTLE_MS] = "invalid_throttle_ms"
        elif retries < 0:
            errors[CONF_RETRIES] = "invalid_retries"

        if errors:
            if source == "import":
                return self.async_abort(reason="invalid_yaml")
            schema = self._build_schema(user_input)
            return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

        normalized = dict(user_input)
        normalized[CONF_HOST] = host
        normalized[CONF_TRANSPORT] = transport
        normalized[CONF_PORT] = port
        normalized[CONF_SLAVE_ID] = slave_id
        normalized[CONF_SCAN_INTERVAL] = scan_interval
        normalized[CONF_TIMEOUT] = timeout
        normalized[CONF_THROTTLE_MS] = throttle_ms
        normalized[CONF_RETRIES] = retries

        await self.async_set_unique_id(f"{host}:{port}:{slave_id}:{transport}")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=f"Haier ATW ({host})", data=normalized)

    def _build_schema(self, defaults: dict[str, Any] | None = None) -> vol.Schema:
        defaults = defaults or {}
        return vol.Schema(
            {
                vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
                vol.Optional(CONF_TRANSPORT, default=defaults.get(CONF_TRANSPORT, TRANSPORT_MODBUS_TCP)): vol.In(
                    [TRANSPORT_MODBUS_TCP, TRANSPORT_EW11_RTU_OVER_TCP]
                ),
                vol.Optional(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): vol.Coerce(int),
                vol.Optional(CONF_SLAVE_ID, default=defaults.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID)): vol.Coerce(int),
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                ): vol.Coerce(int),
                vol.Optional(CONF_TIMEOUT, default=defaults.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)): vol.Coerce(float),
                vol.Optional(
                    CONF_THROTTLE_MS, default=defaults.get(CONF_THROTTLE_MS, DEFAULT_THROTTLE_MS)
                ): vol.Coerce(int),
                vol.Optional(CONF_RETRIES, default=defaults.get(CONF_RETRIES, DEFAULT_RETRIES)): vol.Coerce(int),
            }
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return await self._validate_and_create_entry(user_input, source="user")
        return self.async_show_form(step_id="user", data_schema=self._build_schema(), errors={})

    async def async_step_import(self, user_input: dict[str, Any]) -> FlowResult:
        return await self._validate_and_create_entry(user_input, source="import")
