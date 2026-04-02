import json
import yaml
from click.testing import CliRunner
from agentic_stacks_cli import cli


def _create_operator_project(path, parent_pulled=False):
    """Helper to create a minimal operator project for testing."""
    path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "my-cloud", "namespace": "blahfoo",
        "version": "0.1.0", "description": "My cloud",
        "extends": {
            "name": "openstack-kolla",
            "namespace": "agentic-stacks",
            "version": "1.3.0",
        },
    }
    (path / "stack.yaml").write_text(yaml.dump(manifest, sort_keys=False))
    (path / "environments").mkdir()
    (path / "state").mkdir()

    env = path / "environments" / "prod"
    env.mkdir()
    (env / "config.yml").write_text(yaml.dump({"name": "prod"}))

    if parent_pulled:
        parent_dir = (path / ".stacks" / "agentic-stacks" /
                      "openstack-kolla" / "1.3.0")
        parent_dir.mkdir(parents=True)
        parent_manifest = {
            "name": "openstack-kolla", "namespace": "agentic-stacks",
            "version": "1.3.0", "description": "Parent stack",
            "skills": [{"name": "deploy", "entry": "skills/deploy/",
                        "description": "Deploy"}],
            "project": {
                "environments": True,
                "per_environment": ["config.yml", "inventory/", "files/"],
            },
        }
        (parent_dir / "stack.yaml").write_text(
            yaml.dump(parent_manifest, sort_keys=False))
        (parent_dir / "skills").mkdir()
        (parent_dir / "skills" / "deploy").mkdir()


def test_doctor_operator_project_with_parent(tmp_path):
    proj = tmp_path / "proj"
    _create_operator_project(proj, parent_pulled=True)
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--path", str(proj)])
    assert result.exit_code == 0
    assert "extends" in result.output.lower() or "openstack-kolla" in result.output


def test_doctor_operator_project_missing_parent(tmp_path):
    proj = tmp_path / "proj"
    _create_operator_project(proj, parent_pulled=False)
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--path", str(proj)])
    # Should warn but not fail
    assert result.exit_code == 0
    assert "pull" in result.output.lower()


def test_doctor_operator_project_lists_environments(tmp_path):
    proj = tmp_path / "proj"
    _create_operator_project(proj, parent_pulled=True)
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--path", str(proj)])
    assert "prod" in result.output


def test_doctor_still_works_for_regular_stacks(tmp_path):
    """Existing doctor behavior unaffected."""
    path = tmp_path / "stack"
    path.mkdir()
    manifest = {
        "name": "test", "namespace": "testorg", "version": "1.0.0",
        "description": "Test",
        "skills": [{"name": "deploy", "entry": "skills/deploy/",
                    "description": "Deploy"}],
        "profiles": {"categories": ["security"], "path": "profiles/"},
        "environment_schema": "environments/_schema.json",
    }
    (path / "stack.yaml").write_text(yaml.dump(manifest, sort_keys=False))
    (path / "skills").mkdir()
    (path / "skills" / "deploy").mkdir()
    (path / "profiles").mkdir()
    (path / "profiles" / "security").mkdir()
    (path / "environments").mkdir()
    (path / "environments" / "_schema.json").write_text(
        json.dumps({"type": "object", "required": ["name"]}))

    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--path", str(path)])
    assert result.exit_code == 0
    assert "healthy" in result.output.lower()
