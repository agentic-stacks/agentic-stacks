import yaml
from click.testing import CliRunner
from agentic_stacks_cli import cli


def test_init_with_positional_args(tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["init", "agentic-stacks/kubernetes-talos", str(tmp_path / "my-cluster")])
    assert result.exit_code == 0, result.output
    target = tmp_path / "my-cluster"
    assert (target / "CLAUDE.md").exists()
    assert (target / "stacks.lock").exists()
    assert (target / ".gitignore").exists()
    assert not (target / "skills").exists()


def test_init_infers_path_from_name(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(cli, ["init", "agentic-stacks/kubernetes-talos"])
        assert result.exit_code == 0, result.output
        import pathlib
        assert (pathlib.Path(td) / "kubernetes-talos" / "stacks.lock").exists()


def test_init_stacks_lock_content(tmp_path):
    runner = CliRunner()
    runner.invoke(cli, ["init", "myorg/my-stack", str(tmp_path / "proj")])
    lock = yaml.safe_load((tmp_path / "proj" / "stacks.lock").read_text())
    assert lock["stacks"][0]["name"] == "myorg/my-stack"
    assert lock["stacks"][0]["repository"] == "https://github.com/myorg/my-stack"


def test_init_claude_md_references_stack(tmp_path):
    runner = CliRunner()
    runner.invoke(cli, ["init", "agentic-stacks/kubernetes-talos", str(tmp_path / "proj")])
    claude = (tmp_path / "proj" / "CLAUDE.md").read_text()
    assert "kubernetes-talos" in claude
    assert ".stacks/" in claude


def test_init_existing_directory_fails(tmp_path):
    target = tmp_path / "existing"
    target.mkdir()
    (target / "file.txt").write_text("content")
    runner = CliRunner()
    result = runner.invoke(cli, ["init", "org/name", str(target)])
    assert result.exit_code != 0


def test_init_deprecated_flags_still_work(tmp_path):
    """Old --name/--namespace/--from syntax works with deprecation warning."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        "init", str(tmp_path / "proj"),
        "--name", "my-proj",
        "--namespace", "myorg",
        "--from", "agentic-stacks/openstack-kolla",
    ])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "proj" / "stacks.lock").exists()
    assert "deprecated" in result.output.lower()


def test_init_deprecated_flags_create_stack(tmp_path):
    """Old init without --from creates a stack (backwards compat) with deprecation warning."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        "init", str(tmp_path / "my-stack"),
        "--name", "my-stack",
        "--namespace", "myorg",
    ])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "my-stack" / "stack.yaml").exists()
    assert "deprecated" in result.output.lower()
