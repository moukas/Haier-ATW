from __future__ import annotations

from custom_components.haier_atw_ew11.profiles import (
    DEFAULT_PROFILE_ID,
    list_profile_options,
    load_profile,
    normalize_profile_id,
)


def test_profile_options_expose_default_and_compact() -> None:
    options = list_profile_options()
    assert DEFAULT_PROFILE_ID in options
    assert "haier_compact_auxxfychra" in options


def test_unknown_profile_falls_back_to_default() -> None:
    assert normalize_profile_id("unknown") == DEFAULT_PROFILE_ID
    profile = load_profile("unknown")
    assert profile["id"] == DEFAULT_PROFILE_ID


def test_compact_profile_uses_register_base_zero_and_inverted_power() -> None:
    profile = load_profile("haier_compact_auxxfychra")
    assert profile["register_base"] == 0
    assert profile["special"]["power"]["on_value"] == 0
    assert profile["special"]["power"]["off_value"] == 1
    assert profile["current_temperature_register"] == 8
