"""End-to-end test: load a stack, merge profiles, validate env, diff, track state."""
import json
from agentic_stacks import (
    load_manifest,
    load_profiles_by_category,
    merge_profiles,
    load_environment,
    validate_environment,
    diff_configs,
    StateStore,
    ApprovalGate,
    ApprovalTier,
)


def test_full_pipeline(sample_stack_path, tmp_path):
    # 1. Load manifest
    manifest = load_manifest(sample_stack_path / "stack.yaml")
    assert manifest["full_name"] == "test/sample-stack"

    # 2. Load environment
    env = load_environment(sample_stack_path / "environments" / "dev")
    assert env["name"] == "dev"

    # 3. Validate environment against schema
    schema = json.loads(
        (sample_stack_path / "environments" / "_schema.json").read_text()
    )
    validate_environment(env, schema)

    # 4. Load and merge profiles based on environment selections
    profiles = load_profiles_by_category(
        sample_stack_path / "profiles",
        selections=env["profiles"],
        category_order=manifest["profiles"]["categories"],
    )
    merged = merge_profiles(profiles, enforced_marker="enforced")
    assert merged["security"]["tls_required"] is True
    assert merged["networking"]["driver"] == "option-a"

    # 5. Diff against a hypothetical "current" config
    current = {"security": {"tls_required": True}, "networking": {"driver": "option-b"}}
    diffs = diff_configs(current, merged)
    changed_paths = {d.path for d in diffs}
    assert "networking.driver" in changed_paths

    # 6. Approval gate
    tier = ApprovalTier.from_string(env["approval"]["tier"])
    gate = ApprovalGate(tier=tier)
    result = gate.request(
        action="deploy",
        environment=env["name"],
        description="Deploy dev environment",
    )
    assert result.approved is True

    # 7. Track in state store
    store = StateStore(tmp_path / "state.jsonl")
    store.append(
        action="deploy",
        environment=env["name"],
        actor="agent",
        outcome="success",
        details={"stack": manifest["full_name"], "version": manifest["version"]},
    )
    last = store.last(environment="dev")
    assert last["outcome"] == "success"
    assert last["details"]["stack"] == "test/sample-stack"
