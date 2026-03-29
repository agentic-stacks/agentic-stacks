import pathlib
import yaml
from click.testing import CliRunner

from agentic_stacks_cli import cli

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def test_init_from_local_path_deprecated(tmp_path):
    """Old --from with local path still works."""
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
    assert "deprecated" in result.output.lower()


def test_init_from_github_ref_deprecated(tmp_path):
    """Old --from with GitHub reference still works."""
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


def test_init_positional_github_ref(tmp_path):
    """New positional syntax with owner/name."""
    target = tmp_path / "my-cloud"
    runner = CliRunner()
    result = runner.invoke(cli, ["init", "agentic-stacks/openstack-kolla", str(target)])
    assert result.exit_code == 0, result.output
    lock = yaml.safe_load((target / "stacks.lock").read_text())
    assert lock["stacks"][0]["name"] == "agentic-stacks/openstack-kolla"
    assert lock["stacks"][0]["repository"] == "https://github.com/agentic-stacks/openstack-kolla"
    assert not (target / "skills").exists()


def test_init_positional_claude_md(tmp_path):
    """New syntax generates CLAUDE.md pointing to stack."""
    target = tmp_path / "proj"
    runner = CliRunner()
    runner.invoke(cli, ["init", "agentic-stacks/openstack-kolla", str(target)])
    claude = (target / "CLAUDE.md").read_text()
    assert "openstack-kolla" in claude
    assert ".stacks/" in claude


def test_init_positional_gitignore(tmp_path):
    target = tmp_path / "proj"
    runner = CliRunner()
    runner.invoke(cli, ["init", "agentic-stacks/openstack-kolla", str(target)])
    content = (target / ".gitignore").read_text()
    assert ".stacks/" in content
