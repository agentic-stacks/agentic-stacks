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
    bad_manifest.write_text("description: missing name\n")
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


def test_manifest_owner_field(tmp_path):
    """Manifest with 'owner' field loads correctly."""
    manifest_file = tmp_path / "stack.yaml"
    manifest_file.write_text(
        "name: my-stack\nowner: my-org\nversion: '1.0.0'\ndescription: test\n"
    )
    manifest = load_manifest(manifest_file)
    assert manifest["owner"] == "my-org"
    assert manifest["full_name"] == "my-org/my-stack"


def test_manifest_namespace_backwards_compat(tmp_path):
    """Manifest with 'namespace' but no 'owner' maps namespace to owner."""
    manifest_file = tmp_path / "stack.yaml"
    manifest_file.write_text(
        "name: my-stack\nnamespace: legacy-org\nversion: '1.0.0'\ndescription: test\n"
    )
    manifest = load_manifest(manifest_file)
    assert manifest["owner"] == "legacy-org"
    assert manifest["full_name"] == "legacy-org/my-stack"


def test_manifest_owner_takes_precedence(tmp_path):
    """When both 'owner' and 'namespace' exist, 'owner' wins."""
    manifest_file = tmp_path / "stack.yaml"
    manifest_file.write_text(
        "name: my-stack\nowner: new-org\nnamespace: old-org\n"
        "version: '1.0.0'\ndescription: test\n"
    )
    manifest = load_manifest(manifest_file)
    assert manifest["owner"] == "new-org"
    assert manifest["full_name"] == "new-org/my-stack"


def test_manifest_neither_owner_nor_namespace_fails(tmp_path):
    """Manifest with neither 'owner' nor 'namespace' fails validation."""
    manifest_file = tmp_path / "stack.yaml"
    manifest_file.write_text(
        "name: my-stack\nversion: '1.0.0'\ndescription: test\n"
    )
    with pytest.raises(ManifestError, match="owner"):
        load_manifest(manifest_file)
