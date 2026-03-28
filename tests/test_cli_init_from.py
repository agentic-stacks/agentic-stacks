import pathlib
import yaml
from click.testing import CliRunner

from agentic_stacks_cli import cli

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def test_init_from_creates_structure(tmp_path):
    target = tmp_path / "my-cloud"
    runner = CliRunner()
    result = runner.invoke(cli, [
        "init", str(target),
        "--name", "my-cloud",
        "--namespace", "blahfoo",
        "--from", f"{FIXTURES / 'parent-stack'}",
    ])
    assert result.exit_code == 0, result.output

    assert (target / "stack.yaml").exists()
    assert (target / "environments").is_dir()
    assert (target / "state").is_dir()
    assert (target / "stacks.lock").exists()
    assert (target / ".gitignore").exists()
    assert (target / "CLAUDE.md").exists()

    # Operator projects do NOT have skills/ or profiles/
    assert not (target / "skills").exists()
    assert not (target / "profiles").exists()


def test_init_from_stack_yaml_has_extends(tmp_path):
    target = tmp_path / "my-cloud"
    runner = CliRunner()
    runner.invoke(cli, [
        "init", str(target),
        "--name", "my-cloud",
        "--namespace", "blahfoo",
        "--from", f"{FIXTURES / 'parent-stack'}",
    ])

    manifest = yaml.safe_load((target / "stack.yaml").read_text())
    assert manifest["name"] == "my-cloud"
    assert manifest["namespace"] == "blahfoo"
    assert manifest["extends"]["name"] == "openstack-kolla"
    assert manifest["extends"]["namespace"] == "agentic-stacks"
    assert manifest["extends"]["version"] == "1.3.0"


def test_init_from_creates_example_environment(tmp_path):
    target = tmp_path / "my-cloud"
    runner = CliRunner()
    runner.invoke(cli, [
        "init", str(target),
        "--name", "my-cloud",
        "--namespace", "blahfoo",
        "--from", f"{FIXTURES / 'parent-stack'}",
    ])

    example_env = target / "environments" / "example"
    assert example_env.is_dir()
    assert (example_env / "config.yml").exists()
    assert (example_env / "inventory").is_dir()
    assert (example_env / "files").is_dir()
    assert (example_env / "secrets").is_dir()

    config = yaml.safe_load((example_env / "config.yml").read_text())
    assert config["name"] == "example"


def test_init_from_stacks_lock(tmp_path):
    target = tmp_path / "my-cloud"
    runner = CliRunner()
    runner.invoke(cli, [
        "init", str(target),
        "--name", "my-cloud",
        "--namespace", "blahfoo",
        "--from", f"{FIXTURES / 'parent-stack'}",
    ])

    lock = yaml.safe_load((target / "stacks.lock").read_text())
    assert lock["stacks"][0]["name"] == "agentic-stacks/openstack-kolla"
    assert lock["stacks"][0]["version"] == "1.3.0"


def test_init_from_gitignore(tmp_path):
    target = tmp_path / "my-cloud"
    runner = CliRunner()
    runner.invoke(cli, [
        "init", str(target),
        "--name", "my-cloud",
        "--namespace", "blahfoo",
        "--from", f"{FIXTURES / 'parent-stack'}",
    ])

    content = (target / ".gitignore").read_text()
    assert ".stacks/" in content


def test_init_from_claude_md_references_stack(tmp_path):
    target = tmp_path / "my-cloud"
    runner = CliRunner()
    runner.invoke(cli, [
        "init", str(target),
        "--name", "my-cloud",
        "--namespace", "blahfoo",
        "--from", f"{FIXTURES / 'parent-stack'}",
    ])

    claude = (target / "CLAUDE.md").read_text()
    assert "openstack-kolla" in claude
    assert ".stacks/" in claude
    assert "deploy" in claude.lower()


def test_init_from_no_project_field_uses_defaults(tmp_path):
    """A stack without a project field still works — just no per_environment dirs."""
    target = tmp_path / "my-stack"
    runner = CliRunner()
    result = runner.invoke(cli, [
        "init", str(target),
        "--name", "my-thing",
        "--namespace", "myorg",
        "--from", f"{FIXTURES / 'sample-stack'}",
    ])
    assert result.exit_code == 0, result.output
    assert (target / "stack.yaml").exists()
    assert (target / "environments").is_dir()

    example_env = target / "environments" / "example"
    assert example_env.is_dir()
    assert (example_env / "config.yml").exists()
    # No inventory/ etc. because sample-stack has no project.per_environment
    assert not (example_env / "inventory").exists()


def test_init_without_from_unchanged(tmp_path):
    """Existing init behavior is not affected."""
    target = tmp_path / "regular-stack"
    runner = CliRunner()
    result = runner.invoke(cli, [
        "init", str(target),
        "--name", "my-stack",
        "--namespace", "test",
    ])
    assert result.exit_code == 0
    assert (target / "skills").is_dir()
    assert (target / "profiles").is_dir()

    manifest = yaml.safe_load((target / "stack.yaml").read_text())
    assert manifest.get("extends") is None


def test_init_from_bad_path(tmp_path):
    target = tmp_path / "bad"
    runner = CliRunner()
    result = runner.invoke(cli, [
        "init", str(target),
        "--name", "x",
        "--namespace", "y",
        "--from", "/nonexistent/path",
    ])
    assert result.exit_code != 0
