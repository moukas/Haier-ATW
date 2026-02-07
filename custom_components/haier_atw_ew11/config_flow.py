from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_SLAVE_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SLAVE_ID,
    DEFAULT_SCAN_INTERVAL,
)

class HaierAtwConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}

        if user_input is not None:
            # Basic validation
            host = user_input[CONF_HOST].strip()
            if not host:
                errors[CONF_HOST] = "required"
            else:
                await self.async_set_unique_id(f"{host}:{user_input[CONF_PORT]}:{user_input[CONF_SLAVE_ID]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"Haier ATW ({host})", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
                vol.Optional(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): vol.Coerce(int),
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.Coerce(int),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
