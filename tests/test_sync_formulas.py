import pathlib
import yaml
import importlib.util

spec = importlib.util.spec_from_file_location(
    "sync_formulas",
    pathlib.Path(__file__).parent.parent / "scripts" / "sync_formulas.py",
)
sync = importlib.util.module_from_spec(spec)


def _load_sync():
    spec.loader.exec_module(sync)
    return sync


def test_manifest_to_formula():
    mod = _load_sync()
    manifest = {
        "name": "test-stack",
        "owner": "test-org",
        "version": "0.1.0",
        "description": "A test stack",
        "repository": "https://github.com/test-org/test-stack",
        "target": {"software": "test", "versions": ["1.0"]},
        "skills": [
            {"name": "deploy", "entry": "skills/deploy", "description": "Deploy it"},
            {"name": "diagnose", "entry": "skills/diagnose", "description": "Fix it"},
        ],
        "depends_on": [],
        "requires": {"tools": [{"name": "test-tool", "description": "A tool"}], "python": ">=3.11"},
    }
    formula = mod.manifest_to_formula(manifest)
    assert formula["name"] == "test-stack"
    assert formula["owner"] == "test-org"
    assert formula["repository"] == "https://github.com/test-org/test-stack"
    assert formula["tag"] == "v0.1.0"
    assert formula["sha256"] == ""
    # Skills should not include 'entry' field
    assert "entry" not in formula["skills"][0]
    assert formula["skills"][0]["name"] == "deploy"
    # Tools should be flattened to names
    assert formula["requires"]["tools"] == ["test-tool"]


def test_manifest_to_formula_namespace_fallback():
    """Supports old manifests with 'namespace' instead of 'owner'."""
    mod = _load_sync()
    manifest = {
        "name": "old-stack",
        "namespace": "old-org",
        "version": "1.0.0",
        "description": "Old style",
        "repository": "https://github.com/old-org/old-stack",
        "target": {"software": "test", "versions": []},
        "skills": [],
        "depends_on": [],
        "requires": {},
    }
    formula = mod.manifest_to_formula(manifest)
    assert formula["owner"] == "old-org"


def test_write_formulas_to_directory(tmp_path):
    mod = _load_sync()
    formulas = [
        {
            "name": "stack-a",
            "owner": "org-a",
            "version": "1.0.0",
            "repository": "https://github.com/org-a/stack-a",
            "tag": "v1.0.0",
            "sha256": "",
            "description": "Stack A",
            "target": {},
            "skills": [],
            "depends_on": [],
            "requires": {},
        },
    ]
    mod.write_formulas(tmp_path, formulas)
    written = tmp_path / "stacks" / "org-a" / "stack-a.yaml"
    assert written.exists()
    loaded = yaml.safe_load(written.read_text())
    assert loaded["name"] == "stack-a"
