"""Profile loading, category ordering, and deep merge with enforced key protection."""

import copy
import pathlib
from typing import Any

import yaml


class EnforcedKeyError(Exception):
    """Raised when a merge attempts to override an enforced key."""
    pass


def load_profile(path: pathlib.Path) -> dict:
    """Load a single YAML profile file."""
    path = pathlib.Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path}")
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Profile must be a YAML mapping: {path}")
    return data


def load_profiles_by_category(
    profiles_dir: pathlib.Path,
    selections: dict[str, str],
    category_order: list[str],
) -> list[dict]:
    """Load profiles in category order based on selections.

    Args:
        profiles_dir: Root profiles/ directory.
        selections: Mapping of category name to profile name.
        category_order: Order in which to load categories.

    Returns:
        List of profile dicts, ordered by category_order.
    """
    profiles_dir = pathlib.Path(profiles_dir)
    result = []
    for category in category_order:
        if category not in selections:
            continue
        profile_name = selections[category]
        profile_path = profiles_dir / category / f"{profile_name}.yml"
        result.append(load_profile(profile_path))
    return result


def _collect_enforced_keys(data: dict, marker: str, path: str = "") -> dict[str, Any]:
    """Walk a dict and collect keys that are siblings of an enforced marker."""
    enforced = {}
    if isinstance(data, dict):
        if data.get(marker) is True:
            for key, value in data.items():
                if key != marker:
                    full_key = f"{path}.{key}" if path else key
                    enforced[full_key] = value
        for key, value in data.items():
            if key != marker and isinstance(value, dict):
                child_path = f"{path}.{key}" if path else key
                enforced.update(_collect_enforced_keys(value, marker, child_path))
    return enforced


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base. Returns a new dict."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


_SENTINEL = object()


def _get_nested(data: dict, dotted_key: str) -> Any:
    """Get a value from a nested dict using a dotted key path."""
    keys = dotted_key.split(".")
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return _SENTINEL
        current = current[key]
    return current


def merge_profiles(
    profiles: list[dict],
    enforced_marker: str | None = None,
) -> dict:
    """Merge a list of profiles using deep merge.

    Args:
        profiles: List of profile dicts, in merge order.
        enforced_marker: If set, keys that are siblings of this marker
            cannot be overridden to different values by later profiles.

    Returns:
        Merged profile dict.
    """
    if not profiles:
        return {}

    enforced_keys: dict[str, Any] = {}
    result = {}

    for profile in profiles:
        if enforced_marker:
            for enforced_path, enforced_value in enforced_keys.items():
                new_value = _get_nested(profile, enforced_path)
                if new_value is not _SENTINEL and new_value != enforced_value:
                    raise EnforcedKeyError(
                        f"Cannot override enforced key '{enforced_path}': "
                        f"tried to change {enforced_value!r} to {new_value!r}"
                    )
            enforced_keys.update(
                _collect_enforced_keys(profile, enforced_marker)
            )

        result = _deep_merge(result, profile)

    if enforced_marker:
        _remove_marker(result, enforced_marker)

    return result


def _remove_marker(data: dict, marker: str) -> None:
    """Remove all instances of the enforced marker key from a nested dict."""
    keys_to_remove = [k for k in data if k == marker]
    for key in keys_to_remove:
        del data[key]
    for value in data.values():
        if isinstance(value, dict):
            _remove_marker(value, marker)
