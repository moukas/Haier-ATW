from __future__ import annotations

from functools import lru_cache
import json
import os
from typing import Any

DEFAULT_PROFILE_ID = "haier_atw_ew11"
PROFILE_FILE_SUFFIX = ".profile.json"
PROFILE_DIRNAME = "profiles"

def _base_dir() -> str:
    return os.path.dirname(__file__)


def _profiles_dir() -> str:
    return os.path.join(_base_dir(), PROFILE_DIRNAME)


def _resolve_data_file(path: str) -> str:
    if os.path.isabs(path):
        return path
    in_profiles = os.path.join(_profiles_dir(), path)
    if os.path.exists(in_profiles):
        return in_profiles
    return os.path.join(_base_dir(), path)


def _load_points_from_file(points_file: str) -> list[dict[str, Any]]:
    resolved = _resolve_data_file(points_file)
    with open(resolved, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    return [dict(point) for point in loaded]


@lru_cache(maxsize=1)
def _load_profile_definitions() -> dict[str, dict[str, Any]]:
    definitions: dict[str, dict[str, Any]] = {}
    profiles_dir = _profiles_dir()
    if not os.path.isdir(profiles_dir):
        return definitions

    for filename in sorted(os.listdir(profiles_dir)):
        if not filename.endswith(PROFILE_FILE_SUFFIX):
            continue
        file_path = os.path.join(profiles_dir, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            continue
        profile_id = str(raw.get("id") or filename[: -len(PROFILE_FILE_SUFFIX)]).strip()
        if not profile_id:
            continue
        raw["id"] = profile_id
        raw["_profile_file"] = filename
        definitions[profile_id] = raw
    return definitions


def normalize_profile_id(profile_id: str | None) -> str:
    definitions = _load_profile_definitions()
    candidate = str(profile_id or "").strip()
    if candidate in definitions:
        return candidate
    if DEFAULT_PROFILE_ID in definitions:
        return DEFAULT_PROFILE_ID
    return next(iter(definitions), DEFAULT_PROFILE_ID)


def list_profile_options() -> dict[str, str]:
    definitions = _load_profile_definitions()
    return {
        profile_id: str(defn.get("name", profile_id))
        for profile_id, defn in definitions.items()
    }


def load_profile(profile_id: str | None) -> dict[str, Any]:
    definitions = _load_profile_definitions()
    normalized_id = normalize_profile_id(profile_id)
    definition = definitions.get(normalized_id, {})
    special = {str(key): dict(spec) for key, spec in dict(definition.get("special", {})).items()}
    mode_options = {int(k): str(v) for k, v in dict(definition.get("mode_options", {})).items()}
    mode_to_hvac = {int(k): str(v) for k, v in dict(definition.get("mode_to_hvac", {})).items()}
    hvac_to_mode = {str(k): int(v) for k, v in dict(definition.get("hvac_to_mode", {})).items()}
    return {
        "id": normalized_id,
        "name": str(definition.get("name", normalized_id)),
        "points": _load_points_from_file(str(definition.get("points_file", "points.json"))),
        "register_base": int(definition.get("register_base", 40001)),
        "absolute_addressing_ports": {int(p) for p in definition.get("absolute_addressing_ports", [])},
        "special": special,
        "mode_options": mode_options,
        "mode_to_hvac": mode_to_hvac,
        "hvac_to_mode": hvac_to_mode,
        "current_temperature_register": int(definition.get("current_temperature_register", 40142)),
        "fault_registers": {int(r) for r in definition.get("fault_registers", [])},
    }
