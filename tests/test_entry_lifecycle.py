from __future__ import annotations

import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.haier_atw_ew11.const import DOMAIN

integration = importlib.import_module("custom_components.haier_atw_ew11")


class _FakeCoordinator:
    def __init__(self) -> None:
        self.async_config_entry_first_refresh = AsyncMock()
        self.async_close = AsyncMock()


@pytest.mark.asyncio
async def test_async_setup_and_unload_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[_FakeCoordinator] = []

    def _coordinator_factory(hass, entry):  # noqa: ANN001
        coord = _FakeCoordinator()
        created.append(coord)
        return coord

    monkeypatch.setattr(integration, "HaierAtwCoordinator", _coordinator_factory)

    hass = SimpleNamespace(
        data={},
        config_entries=SimpleNamespace(
            async_forward_entry_setups=AsyncMock(),
            async_unload_platforms=AsyncMock(return_value=True),
        ),
    )
    entry = SimpleNamespace(entry_id="entry-1", data={"host": "127.0.0.1"})

    setup_ok = await integration.async_setup_entry(hass, entry)
    assert setup_ok is True
    hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(entry, integration.PLATFORMS)
    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]
    created[0].async_config_entry_first_refresh.assert_awaited_once()

    unload_ok = await integration.async_unload_entry(hass, entry)
    assert unload_ok is True
    hass.config_entries.async_unload_platforms.assert_awaited_once_with(entry, integration.PLATFORMS)
    created[0].async_close.assert_awaited_once()
    assert entry.entry_id not in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_async_unload_entry_without_stored_coordinator() -> None:
    hass = SimpleNamespace(
        data={},
        config_entries=SimpleNamespace(async_unload_platforms=AsyncMock(return_value=True)),
    )
    entry = SimpleNamespace(entry_id="missing", data={})

    unload_ok = await integration.async_unload_entry(hass, entry)
    assert unload_ok is True
