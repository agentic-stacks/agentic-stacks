from unittest.mock import patch

import yaml
from click.testing import CliRunner
from agentic_stacks_cli import cli


@patch("agentic_stacks_cli.commands.init._pull_common_skills")
def test_init_creates_project_in_named_dir(mock_pull, tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(tmp_path / "my-project")])
    assert result.exit_code == 0, result.output
    target = tmp_path / "my-project"
    assert (target / "CLAUDE.md").exists()
    assert (target / "stacks.lock").exists()
    assert (target / ".gitignore").exists()


@patch("agentic_stacks_cli.commands.init._pull_common_skills")
def test_init_current_directory(mock_pull, tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0, result.output
        import pathlib
        assert (pathlib.Path(".") / "stacks.lock").exists()
        assert (pathlib.Path(".") / "CLAUDE.md").exists()


@patch("agentic_stacks_cli.commands.init._pull_common_skills")
def test_init_empty_stacks_lock(mock_pull, tmp_path):
    runner = CliRunner()
    runner.invoke(cli, ["init", str(tmp_path / "proj")])
    lock = yaml.safe_load((tmp_path / "proj" / "stacks.lock").read_text())
    assert lock["stacks"] == []


@patch("agentic_stacks_cli.commands.init._pull_common_skills")
def test_init_claude_md_has_discovery_instructions(mock_pull, tmp_path):
    runner = CliRunner()
    runner.invoke(cli, ["init", str(tmp_path / "proj")])
    claude = (tmp_path / "proj" / "CLAUDE.md").read_text()
    assert "agentic-stacks search" in claude
    assert "agentic-stacks pull" in claude


def test_init_existing_nonempty_directory_fails(tmp_path):
    target = tmp_path / "existing"
    target.mkdir()
    (target / "stacks.lock").write_text("stacks: []\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(target)])
    assert result.exit_code != 0
    assert "Already initialized" in result.output


@patch("agentic_stacks_cli.commands.init._pull_common_skills")
def test_init_existing_empty_directory_works(mock_pull, tmp_path):
    target = tmp_path / "empty"
    target.mkdir()
    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(target)])
    assert result.exit_code == 0, result.output
    assert (target / "stacks.lock").exists()


@patch("agentic_stacks_cli.commands.init._pull_common_skills")
def test_init_output_suggests_next_steps(mock_pull, tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(tmp_path / "proj")])
    assert "search" in result.output
    assert "pull" in result.output


@patch("agentic_stacks_cli.commands.init._pull_common_skills")
def test_init_pulls_common_skills(mock_pull, tmp_path):
    """Verify _pull_common_skills is called by default."""
    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(tmp_path / "proj")])
    assert result.exit_code == 0, result.output
    mock_pull.assert_called_once()


def test_init_no_common_flag(tmp_path):
    """Verify --no-common skips the common-skills pull."""
    with patch("agentic_stacks_cli.commands.init._pull_common_skills") as mock_pull:
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--no-common", str(tmp_path / "proj")])
        assert result.exit_code == 0, result.output
        mock_pull.assert_not_called()


@patch("agentic_stacks_cli.commands.init._pull_common_skills", side_effect=Exception("network error"))
def test_init_common_skills_failure_non_fatal(mock_pull, tmp_path):
    """Verify init succeeds even if common-skills pull fails."""
    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(tmp_path / "proj")])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "proj" / "stacks.lock").exists()
    assert "Warning" in result.output or "warning" in result.output.lower()
