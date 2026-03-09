from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.haier_atw_ew11.config_flow import HaierAtwConfigFlow
from custom_components.haier_atw_ew11.const import (
    DEFAULT_RTU_OVER_TCP_PORT,
    DEFAULT_NAME,
    CONF_NAME,
    CONF_HOST,
    CONF_PORT,
    CONF_PROFILE,
    CONF_RETRIES,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    CONF_THROTTLE_MS,
    CONF_TIMEOUT,
    CONF_TRANSPORT,
    DEFAULT_PROFILE,
)


@pytest.mark.asyncio
async def test_config_flow_shows_initial_form() -> None:
    flow = HaierAtwConfigFlow()
    result = await flow.async_step_user()

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}


@pytest.mark.asyncio
async def test_config_flow_validates_user_input() -> None:
    flow = HaierAtwConfigFlow()

    result = await flow.async_step_user(
        {
            CONF_NAME: "Tepelko",
            CONF_HOST: " ",
            CONF_PORT: 502,
            CONF_SLAVE_ID: 1,
            CONF_SCAN_INTERVAL: 10,
            CONF_TIMEOUT: 1.0,
            CONF_THROTTLE_MS: 0,
            CONF_RETRIES: 0,
            CONF_TRANSPORT: "modbus_tcp",
        }
    )
    assert result["type"] == "form"
    assert result["errors"][CONF_HOST] == "required"

    result = await flow.async_step_user(
        {
            CONF_NAME: "Tepelko",
            CONF_HOST: "127.0.0.1",
            CONF_PORT: 0,
            CONF_SLAVE_ID: 1,
            CONF_SCAN_INTERVAL: 10,
            CONF_TIMEOUT: 1.0,
            CONF_THROTTLE_MS: 0,
            CONF_RETRIES: 0,
            CONF_TRANSPORT: "modbus_tcp",
        }
    )
    assert result["errors"][CONF_PORT] == "invalid_port"

    result = await flow.async_step_user(
        {
            CONF_NAME: "Tepelko",
            CONF_HOST: "127.0.0.1",
            CONF_PORT: 502,
            CONF_SLAVE_ID: 0,
            CONF_SCAN_INTERVAL: 10,
            CONF_TIMEOUT: 1.0,
            CONF_THROTTLE_MS: 0,
            CONF_RETRIES: 0,
            CONF_TRANSPORT: "modbus_tcp",
        }
    )
    assert result["errors"][CONF_SLAVE_ID] == "invalid_slave_id"

    result = await flow.async_step_user(
        {
            CONF_NAME: "Tepelko",
            CONF_HOST: "127.0.0.1",
            CONF_PORT: 502,
            CONF_SLAVE_ID: 1,
            CONF_SCAN_INTERVAL: 0,
            CONF_TIMEOUT: 1.0,
            CONF_THROTTLE_MS: 0,
            CONF_RETRIES: 0,
            CONF_TRANSPORT: "modbus_tcp",
        }
    )
    assert result["errors"][CONF_SCAN_INTERVAL] == "invalid_scan_interval"


@pytest.mark.asyncio
async def test_config_flow_creates_entry_with_trimmed_host(monkeypatch: pytest.MonkeyPatch) -> None:
    flow = HaierAtwConfigFlow()
    set_unique_id = AsyncMock()
    monkeypatch.setattr(flow, "async_set_unique_id", set_unique_id)
    monkeypatch.setattr(flow, "_abort_if_unique_id_configured", lambda: None)

    result = await flow.async_step_user(
        {
            CONF_NAME: "  Tepelko Dum  ",
            CONF_HOST: " 192.168.1.10 ",
            CONF_PORT: 502,
            CONF_SLAVE_ID: 1,
            CONF_SCAN_INTERVAL: 10,
            CONF_TIMEOUT: 2.5,
            CONF_THROTTLE_MS: 10,
            CONF_RETRIES: 2,
            CONF_TRANSPORT: "rtu_over_tcp",
        }
    )

    assert result["type"] == "create_entry"
    assert result["title"] == "Tepelko Dum"
    assert result["data"][CONF_NAME] == "Tepelko Dum"
    assert result["data"][CONF_HOST] == "192.168.1.10"
    assert result["data"][CONF_TRANSPORT] == "rtu_over_tcp"
    assert result["data"][CONF_PROFILE] == DEFAULT_PROFILE
    assert result["data"][CONF_PORT] == DEFAULT_RTU_OVER_TCP_PORT
    assert result["data"][CONF_TIMEOUT] == 2.5
    assert result["data"][CONF_THROTTLE_MS] == 10
    assert result["data"][CONF_RETRIES] == 2
    set_unique_id.assert_awaited_once_with(
        f"192.168.1.10:{DEFAULT_RTU_OVER_TCP_PORT}:1:rtu_over_tcp"
    )


@pytest.mark.asyncio
async def test_config_flow_import_sets_default_name_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    flow = HaierAtwConfigFlow()
    set_unique_id = AsyncMock()
    monkeypatch.setattr(flow, "async_set_unique_id", set_unique_id)
    monkeypatch.setattr(flow, "_abort_if_unique_id_configured", lambda: None)

    result = await flow.async_step_import(
        {
            CONF_HOST: "192.168.1.10",
            CONF_PORT: 8899,
            CONF_SLAVE_ID: 1,
            CONF_SCAN_INTERVAL: 10,
            CONF_TIMEOUT: 2.5,
            CONF_THROTTLE_MS: 10,
            CONF_RETRIES: 2,
            CONF_TRANSPORT: "modbus_tcp",
        }
    )

    assert result["type"] == "create_entry"
    assert result["title"] == DEFAULT_NAME
    assert result["data"][CONF_NAME] == DEFAULT_NAME
    assert result["data"][CONF_PROFILE] == DEFAULT_PROFILE


@pytest.mark.asyncio
async def test_config_flow_accepts_explicit_profile_choice(monkeypatch: pytest.MonkeyPatch) -> None:
    flow = HaierAtwConfigFlow()
    set_unique_id = AsyncMock()
    monkeypatch.setattr(flow, "async_set_unique_id", set_unique_id)
    monkeypatch.setattr(flow, "_abort_if_unique_id_configured", lambda: None)

    result = await flow.async_step_user(
        {
            CONF_NAME: "Compact",
            CONF_HOST: "192.168.1.20",
            CONF_PORT: 502,
            CONF_SLAVE_ID: 1,
            CONF_SCAN_INTERVAL: 10,
            CONF_TIMEOUT: 2.5,
            CONF_THROTTLE_MS: 10,
            CONF_RETRIES: 2,
            CONF_TRANSPORT: "modbus_tcp",
            CONF_PROFILE: "haier_compact_auxxfychra",
        }
    )

    assert result["type"] == "create_entry"
    assert result["data"][CONF_PROFILE] == "haier_compact_auxxfychra"
