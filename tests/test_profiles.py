import pytest
from agentic_stacks.profiles import (
    load_profile,
    load_profiles_by_category,
    merge_profiles,
    EnforcedKeyError,
)


def test_load_single_profile(sample_profiles_path):
    profile = load_profile(sample_profiles_path / "security" / "baseline.yml")
    assert profile["security"]["level"] == "baseline"
    assert profile["security"]["enforced"] is True


def test_load_profiles_by_category(sample_profiles_path):
    profiles = load_profiles_by_category(
        sample_profiles_path,
        selections={"security": "baseline", "networking": "option-a", "storage": "default"},
        category_order=["security", "networking", "storage"],
    )
    assert len(profiles) == 3
    assert profiles[0]["security"]["level"] == "baseline"
    assert profiles[1]["networking"]["driver"] == "option-a"
    assert profiles[2]["storage"]["backend"] == "local"


def test_load_missing_profile_raises(sample_profiles_path):
    with pytest.raises(FileNotFoundError):
        load_profiles_by_category(
            sample_profiles_path,
            selections={"security": "nonexistent"},
            category_order=["security"],
        )


def test_merge_profiles_basic():
    profiles = [
        {"a": 1, "b": {"x": 10}},
        {"b": {"y": 20}, "c": 3},
    ]
    result = merge_profiles(profiles)
    assert result == {"a": 1, "b": {"x": 10, "y": 20}, "c": 3}


def test_merge_profiles_later_overrides_earlier():
    profiles = [
        {"a": 1, "b": {"x": 10}},
        {"a": 2, "b": {"x": 99}},
    ]
    result = merge_profiles(profiles)
    assert result["a"] == 2
    assert result["b"]["x"] == 99


def test_merge_profiles_enforced_keys_protected():
    profiles = [
        {"security": {"tls_required": True, "enforced": True}},
        {"security": {"tls_required": False}},
    ]
    with pytest.raises(EnforcedKeyError, match="tls_required"):
        merge_profiles(profiles, enforced_marker="enforced")


def test_merge_profiles_enforced_allows_same_value():
    profiles = [
        {"security": {"tls_required": True, "enforced": True}},
        {"security": {"tls_required": True}},
    ]
    result = merge_profiles(profiles, enforced_marker="enforced")
    assert result["security"]["tls_required"] is True


def test_full_profile_pipeline(sample_profiles_path):
    profiles = load_profiles_by_category(
        sample_profiles_path,
        selections={"security": "baseline", "networking": "option-a", "storage": "default"},
        category_order=["security", "networking", "storage"],
    )
    merged = merge_profiles(profiles, enforced_marker="enforced")
    assert merged["security"]["tls_required"] is True
    assert merged["networking"]["driver"] == "option-a"
    assert merged["storage"]["backend"] == "local"
