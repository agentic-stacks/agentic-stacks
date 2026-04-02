import yaml
from click.testing import CliRunner
from agentic_stacks_cli import cli


def test_init_creates_project_in_named_dir(tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(tmp_path / "my-project")])
    assert result.exit_code == 0, result.output
    target = tmp_path / "my-project"
    assert (target / "CLAUDE.md").exists()
    assert (target / "stacks.lock").exists()
    assert (target / ".gitignore").exists()


def test_init_current_directory(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0, result.output
        import pathlib
        assert (pathlib.Path(".") / "stacks.lock").exists()
        assert (pathlib.Path(".") / "CLAUDE.md").exists()


def test_init_empty_stacks_lock(tmp_path):
    runner = CliRunner()
    runner.invoke(cli, ["init", str(tmp_path / "proj")])
    lock = yaml.safe_load((tmp_path / "proj" / "stacks.lock").read_text())
    assert lock["stacks"] == []


def test_init_claude_md_has_discovery_instructions(tmp_path):
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


def test_init_existing_empty_directory_works(tmp_path):
    target = tmp_path / "empty"
    target.mkdir()
    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(target)])
    assert result.exit_code == 0, result.output
    assert (target / "stacks.lock").exists()


def test_init_output_suggests_next_steps(tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(tmp_path / "proj")])
    assert "search" in result.output
    assert "pull" in result.output
