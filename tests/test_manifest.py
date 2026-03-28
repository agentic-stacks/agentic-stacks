import pytest
from agentic_stacks.manifest import load_manifest, ManifestError


def test_load_valid_manifest(sample_stack_path):
    manifest = load_manifest(sample_stack_path / "stack.yaml")
    assert manifest["name"] == "sample-stack"
    assert manifest["namespace"] == "test"
    assert manifest["version"] == "1.0.0"
    assert len(manifest["skills"]) == 2
    assert manifest["skills"][0]["name"] == "deploy"
    assert manifest["profiles"]["categories"] == ["security", "networking", "storage"]
    assert manifest["target"]["versions"] == ["1.0", "2.0"]


def test_load_manifest_missing_file(tmp_path):
    with pytest.raises(ManifestError, match="not found"):
        load_manifest(tmp_path / "nonexistent.yaml")


def test_load_manifest_missing_required_fields(tmp_path):
    bad_manifest = tmp_path / "stack.yaml"
    bad_manifest.write_text("description: missing name and version\n")
    with pytest.raises(ManifestError, match="name"):
        load_manifest(bad_manifest)


def test_manifest_deprecations(sample_stack_path):
    manifest = load_manifest(sample_stack_path / "stack.yaml")
    assert len(manifest["deprecations"]) == 1
    dep = manifest["deprecations"][0]
    assert dep["skill"] == "old-deploy"
    assert dep["replacement"] == "deploy"


def test_manifest_full_name(sample_stack_path):
    manifest = load_manifest(sample_stack_path / "stack.yaml")
    assert manifest["full_name"] == "test/sample-stack"
