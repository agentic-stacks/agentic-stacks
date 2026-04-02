import pathlib
import yaml
from click.testing import CliRunner

from agentic_stacks_cli import cli


def test_init_creates_gitignore(tmp_path):
    target = tmp_path / "proj"
    runner = CliRunner()
    runner.invoke(cli, ["init", str(target)])
    content = (target / ".gitignore").read_text()
    assert ".stacks/" in content


def test_init_nested_path(tmp_path):
    """Init creates intermediate directories."""
    target = tmp_path / "deep" / "nested" / "proj"
    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(target)])
    assert result.exit_code == 0, result.output
    assert (target / "stacks.lock").exists()
