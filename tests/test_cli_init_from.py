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
    assert (target / "CLAUDE.md").exists()
    assert (target / "stacks.lock").exists()
    assert (target / ".gitignore").exists()
    # Should NOT create skills/, profiles/, environments/
    assert not (target / "skills").exists()
    assert not (target / "profiles").exists()


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


def test_init_from_github_ref(tmp_path):
    """--from with a GitHub reference (not a local path)."""
    target = tmp_path / "my-cloud"
    runner = CliRunner()
    result = runner.invoke(cli, [
        "init", str(target),
        "--name", "my-cloud",
        "--namespace", "blahfoo",
        "--from", "agentic-stacks/openstack-kolla",
    ])
    assert result.exit_code == 0, result.output
    lock = yaml.safe_load((target / "stacks.lock").read_text())
    assert lock["stacks"][0]["repository"] == "https://github.com/agentic-stacks/openstack-kolla"


def test_init_from_bare_name(tmp_path):
    """--from with just a name defaults to agentic-stacks org."""
    target = tmp_path / "my-cloud"
    runner = CliRunner()
    result = runner.invoke(cli, [
        "init", str(target),
        "--name", "my-cloud",
        "--namespace", "blahfoo",
        "--from", "openstack-kolla",
    ])
    assert result.exit_code == 0, result.output
    lock = yaml.safe_load((target / "stacks.lock").read_text())
    assert lock["stacks"][0]["name"] == "agentic-stacks/openstack-kolla"


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
