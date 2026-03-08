from __future__ import annotations

from types import SimpleNamespace

from custom_components.haier_atw_ew11.entity_base import HaierAtwEntity


class _FakeEntity(HaierAtwEntity):
    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "fake")


class _FakeCoordinator:
    def __init__(self, *, entry_data: dict, profile_name: str | None = None) -> None:
        self.entry = SimpleNamespace(entry_id="entry-1", data=entry_data)
        if profile_name is not None:
            self.profile = {"name": profile_name}


def test_device_info_contains_host_in_display_name_and_url() -> None:
    coordinator = _FakeCoordinator(
        entry_data={"name": "ATW via EW11", "host": "172.23.86.203", "port": 8123},
        profile_name="Haier ATW via EW11",
    )
    entity = _FakeEntity(coordinator)

    info = entity.device_info
    assert info["name"] == "ATW via EW11 (172.23.86.203)"
    assert info["model"] == "Haier ATW via EW11"
    assert info["configuration_url"] == "http://172.23.86.203:8123"


def test_device_info_falls_back_to_defaults_without_host_or_profile() -> None:
    coordinator = _FakeCoordinator(entry_data={})
    entity = _FakeEntity(coordinator)

    info = entity.device_info
    assert info["name"] == "Haier ATW"
    assert info["model"] == "ATW via EW11"
    assert info["configuration_url"] is None
