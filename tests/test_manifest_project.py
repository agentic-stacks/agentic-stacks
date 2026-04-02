import pathlib
import pytest
import yaml

from agentic_stacks.manifest import load_manifest, ManifestError

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def test_manifest_with_project_field():
    manifest = load_manifest(FIXTURES / "parent-stack" / "stack.yaml")
    assert manifest["name"] == "openstack-kolla"
    assert "project" in manifest
    assert manifest["project"]["environments"] is True
    assert "config.yml" in manifest["project"]["per_environment"]
    assert "inventory/" in manifest["project"]["per_environment"]
    assert "files/" in manifest["project"]["per_environment"]
    assert "secrets/" in manifest["project"]["per_environment"]


def test_manifest_with_docs_sources():
    manifest = load_manifest(FIXTURES / "parent-stack" / "stack.yaml")
    assert "docs_sources" in manifest
    assert "kolla-ansible" in manifest["docs_sources"][0]


def test_manifest_without_project_gets_default():
    manifest = load_manifest(FIXTURES / "sample-stack" / "stack.yaml")
    assert manifest["project"] == {}


def test_manifest_with_extends_field(tmp_path):
    data = {
        "name": "my-cloud", "namespace": "blahfoo",
        "version": "1.0.0", "description": "My cloud",
        "extends": {
            "name": "openstack-kolla",
            "namespace": "agentic-stacks",
            "version": "^1.3",
        },
    }
    path = tmp_path / "stack.yaml"
    path.write_text(yaml.dump(data))
    manifest = load_manifest(path)
    assert manifest["extends"]["name"] == "openstack-kolla"
    assert manifest["extends"]["namespace"] == "agentic-stacks"
    assert manifest["extends"]["version"] == "^1.3"


def test_manifest_without_extends_gets_none():
    manifest = load_manifest(FIXTURES / "parent-stack" / "stack.yaml")
    assert manifest.get("extends") is None
