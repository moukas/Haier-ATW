from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_HOST, CONF_NAME, CONF_PORT, DEFAULT_NAME, DOMAIN
from .coordinator import HaierAtwCoordinator


class HaierAtwEntity(CoordinatorEntity[HaierAtwCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: HaierAtwCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key

    @property
    def device_info(self) -> DeviceInfo:
        entry = self.coordinator.entry
        configured_name = str(entry.data.get(CONF_NAME) or "").strip()
        host = str(entry.data.get(CONF_HOST) or "").strip()
        display_name = configured_name or DEFAULT_NAME
        if host and host not in display_name:
            display_name = f"{display_name} ({host})"

        profile_name = "ATW via EW11"
        profile = getattr(self.coordinator, "profile", None)
        if isinstance(profile, dict):
            candidate = str(profile.get("name") or "").strip()
            if candidate:
                profile_name = candidate

        configuration_url = None
        if host:
            try:
                port = int(entry.data.get(CONF_PORT))
            except (TypeError, ValueError):
                port = None
            configuration_url = f"http://{host}:{port}" if port else f"http://{host}"

        return DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=display_name,
            manufacturer="Haier",
            model=profile_name,
            configuration_url=configuration_url,
        )
